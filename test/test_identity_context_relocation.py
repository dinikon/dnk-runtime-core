"""Регрессии владения Identity и сохранения HTTP dependency overrides."""

import ast
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.identity.application.auth.query.authenticate_by_session.dto import (
    SessionPrincipal,
)
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.access.depends import (
    default_authorization_service,
)
from src.modules.identity.presentation.access.depends import get_authorization_service
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.auth.depends import OptionalRequestContextDep
from src.modules.identity.presentation.auth.depends import (
    require_authenticated_request_context,
)
from src.modules.identity.presentation.auth.depends import (
    get_authenticate_by_session_handler,
)

ROOT = Path(__file__).resolve().parents[1]
LEGACY = (
    "src.modules.shared.domain.identity_context",
    "src.modules.shared.application.access",
    "src.modules.shared.infrastructure.access",
    "src.modules.shared.presentation.access",
    "src.modules.shared.presentation.identity_context",
)


class IdentityImportTests(unittest.TestCase):
    def test_removed_paths_and_identity_package_exports_are_not_used(self):
        for prefix in LEGACY:
            self.assertFalse((ROOT / prefix.replace(".", "/")).exists())
        for path in (ROOT / "src/modules/identity").rglob("__init__.py"):
            self.assertEqual(path.read_text().strip(), "", str(path))
        for folder in ("src", "test", "scripts", "migrations", "helm", "docs"):
            for path in (ROOT / folder).rglob("*"):
                if path == Path(__file__).resolve() or path.suffix not in (
                    ".py",
                    ".md",
                    ".yaml",
                    ".yml",
                ):
                    continue
                text = path.read_text()
                for prefix in LEGACY:
                    self.assertNotIn(prefix, text, str(path))
                    self.assertNotIn(prefix.replace(".", "/"), text, str(path))
                if path.suffix != ".py":
                    continue
                trees = [ast.parse(text)]
                # Deployment fixtures also embed Python in strings.
                for node in ast.walk(trees[0]):
                    if (
                        isinstance(node, ast.Constant)
                        and isinstance(node.value, str)
                        and "from src.modules.identity" in node.value
                    ):
                        try:
                            trees.append(ast.parse(node.value))
                        except SyntaxError:
                            pass
                for tree in trees:
                    for node in ast.walk(tree):
                        if (
                            isinstance(node, ast.ImportFrom)
                            and node.module
                            and node.module.startswith("src.modules.identity")
                        ):
                            target = ROOT / node.module.replace(".", "/")
                            self.assertFalse(
                                target.is_dir(), f"{path}: package import {node.module}"
                            )

    def test_shared_does_not_reexport_identity(self):
        import src.modules.shared as shared
        import src.modules.shared.presentation as presentation

        for name in ("Principal", "RequestContext"):
            self.assertFalse(hasattr(shared, name))
        for name in (
            "AuthenticatedRequestContextDep",
            "OptionalRequestContextDep",
            "AuthorizationServiceDep",
            "get_authorization_service",
        ):
            self.assertFalse(hasattr(presentation, name))

    def test_domain_context_import_does_not_load_outer_layers(self):
        subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
assert 'fastapi' not in sys.modules
assert not any(name.startswith(('src.modules.identity.application', 'src.modules.identity.infrastructure', 'src.modules.identity.presentation')) for name in sys.modules)
""",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_entrypoints_import_in_independent_processes(self):
        for module in (
            "src.modules.identity.infrastructure.persistence.models.user",
            "src.modules.identity.presentation.auth.depends",
            "src.modules.identity.presentation.access.depends",
            "src.modules.identity.presentation.auth.http.router",
            "src.modules.identity.presentation.access.http.router",
            "src.modules.identity.presentation.invitation.http.router",
            "src.modules.identity.presentation.cloud.http.router",
            "src.modules.identity.infrastructure.cloud.bootstrap",
            "src.modules.persistence",
            "src.modules.tenant_persistence",
        ):
            with self.subTest(module=module):
                result = subprocess.run(
                    [sys.executable, "-c", f"import {module}"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


class IdentityContextWiringTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.principal = Principal("user", "tenant", "session", ("member",), ("read",))
        self.app = FastAPI()
        self.use_case = SimpleNamespace(
            execute=AsyncMock(
                return_value=SessionPrincipal(
                    "user", "tenant", "session", ("member",), ("read",)
                )
            )
        )
        self.provider = Mock(return_value=self.use_case)

        # A function, rather than Mock itself, preserves FastAPI's empty signature.
        def provide():
            return self.provider()

        self.app.dependency_overrides[get_authenticate_by_session_handler] = provide

        @self.app.get("/required")
        async def required(
            context: AuthenticatedRequestContextDep, optional: OptionalRequestContextDep
        ):
            return {
                "user_id": context.principal.user_id,
                "tenant_id": context.principal.tenant_id,
                "session_id": context.principal.session_id,
                "roles": context.principal.roles,
                "permissions": context.principal.permissions,
                "request_id": context.request_id,
                "ip": context.ip,
                "user_agent": context.user_agent,
                "same_context": context is optional,
            }

        @self.app.get("/optional")
        async def optional(context: OptionalRequestContextDep):
            return {"anonymous": context.principal is None}

        @self.app.get("/access")
        async def access(service: AuthorizationServiceDep):
            return {
                "allowed": await service.can(
                    user_id=None, tenant_id=None, action="read", resource_type="contact"
                )
            }

    def client(self):
        return AsyncClient(
            transport=ASGITransport(app=self.app, client=("192.0.2.1", 123)),
            base_url="https://tenant.example",
        )

    async def test_handler_preserves_fields_and_dependency_cache(self):
        async with self.client() as client:
            client.cookies.set(dnk_config.AUTH.session_cookie_name, "token")
            response = await client.get(
                "/required", headers={"x-request-id": "req", "user-agent": "test"}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "user_id": "user",
                "tenant_id": "tenant",
                "session_id": "session",
                "roles": ["member"],
                "permissions": ["read"],
                "request_id": "req",
                "ip": "192.0.2.1",
                "user_agent": "test",
                "same_context": True,
            },
        )
        self.provider.assert_called_once_with()
        self.use_case.execute.assert_awaited_once()
        command = self.use_case.execute.await_args.args[0]
        self.assertEqual(
            (command.host, command.session_token),
            ("tenant.example", "token"),
        )

    async def test_anonymous_context_and_unauthorized_response(self):
        self.use_case.execute.return_value = None
        async with self.client() as client:
            self.assertEqual(
                (await client.get("/optional")).json(), {"anonymous": True}
            )
            response = await client.get("/required")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Unauthorized."})

    async def test_authenticated_context_dependency_can_be_overridden(self):
        context = RequestContext(
            principal=self.principal, request_id=None, ip=None, user_agent=None
        )
        self.app.dependency_overrides[require_authenticated_request_context] = (
            lambda: context
        )
        app = FastAPI()
        app.dependency_overrides.update(self.app.dependency_overrides)

        @app.get("/")
        async def endpoint(value: AuthenticatedRequestContextDep):
            return value.principal.user_id

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://tenant.example"
        ) as client:
            self.assertEqual((await client.get("/")).json(), "user")
        self.provider.assert_not_called()

    async def test_authorization_default_state_and_dependency_override(self):
        async with self.client() as client:
            self.assertEqual((await client.get("/access")).json(), {"allowed": True})
            service = SimpleNamespace(can=AsyncMock(return_value=False))
            self.app.state.authorization_service = service
            self.assertEqual((await client.get("/access")).json(), {"allowed": False})
            self.app.dependency_overrides[get_authorization_service] = (
                lambda: default_authorization_service
            )
            self.assertEqual((await client.get("/access")).json(), {"allowed": True})
        service.can.assert_awaited_once_with(
            user_id=None, tenant_id=None, action="read", resource_type="contact"
        )
