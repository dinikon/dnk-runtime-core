"""Identity layer boundaries and tenant adapter/authentication error semantics."""

import ast
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantNotFoundError,
    IdentityTenantUnavailableError,
)
from src.modules.identity.application.auth.query.authenticate_by_session.handler import (
    AuthenticateBySessionHandler,
)
from src.modules.identity.application.auth.query.authenticate_by_session.query import (
    AuthenticateBySessionQuery,
)
from src.modules.identity.infrastructure.auth.tenant_context_reader import (
    TenancyTenantContextReaderAdapter,
)
from src.modules.tenancy.domain.tenant_domain.error import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)
from src.modules.shared.application.network.host import normalize_host

ROOT = Path(__file__).resolve().parents[1]


class IdentityStructureTests(unittest.TestCase):
    def test_dependencies_point_inward(self):
        for layer in ("domain", "application", "infrastructure"):
            for path in (ROOT / "src/modules/identity" / layer).rglob("*.py"):
                for node in ast.walk(ast.parse(path.read_text())):
                    imports = (
                        [node.module]
                        if isinstance(node, ast.ImportFrom)
                        else (
                            [n.name for n in node.names]
                            if isinstance(node, ast.Import)
                            else []
                        )
                    )
                    for name in imports:
                        if not name:
                            continue
                        self.assertNotIn(".presentation", name, str(path))
                        if layer in ("domain", "application"):
                            self.assertNotIn(".infrastructure", name, str(path))
                            self.assertFalse(
                                name.startswith(("fastapi", "sqlalchemy")), str(path)
                            )
                        if layer == "domain":
                            self.assertNotIn(".application", name, str(path))
                        if layer == "application":
                            self.assertFalse(
                                name.startswith("src.modules.tenancy.domain"), str(path)
                            )

    def test_no_legacy_files_or_forwarding_exports(self):
        legacy = (
            "application/ports",
            "application/auth/use_case",
            "application/access_service.py",
            "application/cloud_auth_service.py",
            "presentation/depends",
            "presentation/http",
            "infrastructure/adapter",
            "infrastructure/repository",
        )
        for name in legacy:
            self.assertFalse((ROOT / "src/modules/identity" / name).exists(), name)
        for path in (ROOT / "src/modules/identity").rglob("__init__.py"):
            self.assertFalse(path.read_text().strip(), str(path))
        for path in (ROOT / "src").rglob("*.py"):
            self.assertNotIn("authentication_process", path.read_text(), str(path))
        from src.modules.shared.presentation.http import host
        import src.modules.shared.presentation.http as http

        self.assertFalse(hasattr(host, "normalize_host"))
        self.assertFalse(hasattr(http, "normalize_host"))

    def test_auth_query_has_only_application_inputs(self):
        self.assertEqual(
            [f.name for f in fields(AuthenticateBySessionQuery)],
            ["host", "session_token"],
        )

    def test_host_normalization_contract(self):
        for value, expected in [
            (" EXAMPLE.com:443 ", "example.com"),
            ("a-b.example", "a-b.example"),
            ("x:0", ""),
            ("x:65536", ""),
            ("x:abc", ""),
            ("https://x", ""),
            ("user@x", ""),
            ("x/path", ""),
            ("x..example", ""),
            ("x.", ""),
            ("", ""),
        ]:
            with self.subTest(value=value):
                self.assertEqual(normalize_host(value), expected)


class TenantContextAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_maps_known_errors_preserving_cause_and_message(self):
        for source, target in [
            (TenantHostNotFoundError, IdentityTenantNotFoundError),
            (TenantLoginUnavailableError, IdentityTenantUnavailableError),
        ]:
            error = source("tenant.example")
            reader = TenancyTenantContextReaderAdapter(
                SimpleNamespace(execute=AsyncMock(side_effect=error))
            )
            with self.assertRaises(target) as caught:
                await reader.get_by_host("tenant.example")
            self.assertEqual(str(caught.exception), str(error))
            self.assertIs(caught.exception.__cause__, error)

    async def test_unexpected_error_propagates(self):
        error = RuntimeError("storage failure")
        reader = TenancyTenantContextReaderAdapter(
            SimpleNamespace(execute=AsyncMock(side_effect=error))
        )
        with self.assertRaises(RuntimeError) as caught:
            await reader.get_by_host("tenant.example")
        self.assertIs(caught.exception, error)

    async def test_maps_context_without_leaking_tenancy_dto(self):
        dto = SimpleNamespace(
            tenant_id=uuid4(),
            tenant_domain_id=uuid4(),
            host="tenant.example",
            tenant_status="active",
            domain_status="active",
            api_host="api.example",
        )
        handler = SimpleNamespace(execute=AsyncMock(return_value=dto))
        result = await TenancyTenantContextReaderAdapter(handler).get_by_host(
            "tenant.example"
        )
        self.assertEqual(
            vars(dto), {f.name: getattr(result, f.name) for f in fields(result)}
        )
        self.assertIsNot(result, dto)
        self.assertEqual(handler.execute.await_args.args[0].host, dto.host)

    async def test_authentication_hides_only_expected_tenant_failures(self):
        users, sessions, reader = AsyncMock(), AsyncMock(), AsyncMock()
        handler = AuthenticateBySessionHandler(reader, users, sessions)
        query = AuthenticateBySessionQuery("tenant.example", "token")
        for error in (
            IdentityTenantNotFoundError("missing"),
            IdentityTenantUnavailableError("blocked"),
        ):
            reader.get_by_host.side_effect = error
            self.assertIsNone(await handler.execute(query))
        users.get_by_id.assert_not_awaited()
        sessions.get_session.assert_not_awaited()
        reader.get_by_host.side_effect = RuntimeError("storage")
        with self.assertRaises(RuntimeError):
            await handler.execute(query)

    async def test_missing_credentials_do_not_read_stores(self):
        reader, users, sessions = AsyncMock(), AsyncMock(), AsyncMock()
        handler = AuthenticateBySessionHandler(reader, users, sessions)
        for host, token in [
            (None, "token"),
            ("invalid/host", "token"),
            ("tenant.example", None),
            ("tenant.example", ""),
        ]:
            self.assertIsNone(
                await handler.execute(AuthenticateBySessionQuery(host, token))
            )
        reader.get_by_host.assert_not_awaited()
        users.get_by_id.assert_not_awaited()
        sessions.get_session.assert_not_awaited()
