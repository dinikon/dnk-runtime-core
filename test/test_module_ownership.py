"""Границы Tenancy, Identity email и Control Plane после разделения shared."""

import ast
import importlib
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import Depends, FastAPI, Request

from src.modules.control_plane.presentation.http.trust_boundary import (
    ManagementTrustBoundary,
)
from src.modules.identity.presentation.email.depends import (
    EmailServiceDep,
    get_email_service,
)
from src.modules.shared.presentation.http.trusted_proxy import TrustedProxyHeaders
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.tenancy.presentation.depends.infrastructure import (
    TenantsRepositoryDep,
    TenantDomainsRepositoryDep,
)
from src.modules.identity.presentation.depends.infrastructure import UsersRepositoryDep

ROOT = Path(__file__).resolve().parents[1]
OLD_MODULES = (
    "src.modules.shared.application.persistence.tenant_schema_naming",
    "src.modules.shared.application.persistence.tenant_admission",
    "src.modules.shared.infrastructure.persistence.tenant_base",
    "src.modules.shared.infrastructure.persistence.tenant_gate",
    "src.modules.shared.infrastructure.persistence.tenant_migrations",
    "src.modules.shared.infrastructure.persistence.tenant_migration_metadata",
    "src.modules.shared.infrastructure.persistence.tenant_system_mixin",
    "src.modules.shared.presentation.http.tenant_gate",
    "src.modules.shared.presentation.http.trust_boundary",
    "src.modules.shared.application.email.email_service_port",
    "src.modules.shared.infrastructure.email.system_email_service",
    "src.modules.shared.infrastructure.email.render_system_email",
    "src.modules.shared.infrastructure.email.email_transport_port",
    "src.modules.shared.infrastructure.email.rendered_email_message",
    "src.modules.shared.domain.email.system_email_kind",
    "src.modules.shared.domain.email.send_invitation_variables",
    "src.modules.shared.domain.email.send_otp_code_variables",
)


class ModuleOwnershipTests(unittest.TestCase):
    def test_no_old_paths_or_tenancy_package_imports(self):
        for name in OLD_MODULES:
            self.assertFalse((ROOT / (name.replace(".", "/") + ".py")).exists())
        for path in (ROOT / "src/modules/tenancy").rglob("__init__.py"):
            self.assertEqual(path.read_text().strip(), "", str(path))
        for folder in ("src", "test", "scripts", "helm", "migrations", "docs"):
            for path in (ROOT / folder).rglob("*"):
                if path == Path(__file__).resolve() or path.suffix not in (
                    ".py",
                    ".pyi",
                    ".md",
                    ".yaml",
                    ".yml",
                ):
                    continue
                source = path.read_text()
                for name in OLD_MODULES:
                    self.assertNotIn(name, source, str(path))
                    self.assertNotIn(name.replace(".", "/"), source, str(path))
                if path.suffix != ".py":
                    continue
                trees = [ast.parse(source)]
                for node in ast.walk(trees[0]):
                    if (
                        isinstance(node, ast.Constant)
                        and isinstance(node.value, str)
                        and "from src.modules.tenancy" in node.value
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
                            and node.module.startswith("src.modules.tenancy")
                        ):
                            self.assertFalse(
                                (ROOT / node.module.replace(".", "/")).is_dir(),
                                f"{path}: {node.module}",
                            )

    def test_shared_email_and_http_do_not_own_business_policies(self):
        for folder in (
            "application/email",
            "domain/email",
            "infrastructure/email",
            "presentation/email",
            "presentation/http",
        ):
            for path in (ROOT / "src/modules/shared" / folder).rglob("*.py"):
                source = path.read_text()
                for name in (
                    "src.modules.identity",
                    "src.modules.control_plane",
                    "SEND_OTP_CODE",
                    "SEND_INVITATION",
                    "control_plane_trusted",
                    "allowed_core_fingerprints",
                ):
                    self.assertNotIn(name, source, str(path))
        from src.modules.shared import presentation

        self.assertFalse(hasattr(presentation, "EmailServiceDep"))
        shared_metrics = importlib.import_module(
            "src.modules.shared.infrastructure.observability.metrics"
        )
        self.assertFalse(hasattr(shared_metrics, "oidc_errors"))
        self.assertFalse(hasattr(shared_metrics, "mtls_rejections"))

    def test_migrations_keep_original_directory_and_one_alembic_lock(self):
        from src.modules.tenancy.infrastructure.tenant.persistence import (
            tenant_migrations,
        )
        from src.modules.shared.infrastructure.persistence import (
            global_migrations,
            alembic_lock,
        )

        self.assertEqual(tenant_migrations.MIGRATIONS_PATH, ROOT / "migrations/tenant")
        self.assertIs(
            tenant_migrations.serialized_alembic, alembic_lock.serialized_alembic
        )
        self.assertIs(
            global_migrations.serialized_alembic, alembic_lock.serialized_alembic
        )
        self.assertIsNotNone(tenant_migrations.TenantMigrator().head())

    def test_tenant_base_import_does_not_load_identity_or_routers(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_base import TenantBase, TENANT_SCHEMA_ALIAS
assert TENANT_SCHEMA_ALIAS == "tenant"
assert "fastapi" not in sys.modules
assert "src.modules.identity.presentation.auth.depends" not in sys.modules
assert "src.modules.shared.infrastructure.persistence.database_helper" not in sys.modules
""",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_independent_imports(self):
        for name in (
            "src.modules.tenancy.presentation.tenant.http.tenant_gate",
            "src.modules.tenancy.presentation.depends.application",
            "src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations",
            "src.modules.identity.presentation.email.depends",
            "src.modules.control_plane.presentation.http.trust_boundary",
            "src.modules.shared.infrastructure.jobs.worker",
            "src.modules.shared.infrastructure.events.rabbitmq_integration_event_console_worker",
            "src.modules.persistence",
            "src.modules.tenant_persistence",
        ):
            with self.subTest(module=name):
                result = subprocess.run(
                    [sys.executable, "-c", f"import {name}"],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_app_checks_management_before_tenant_admission(self):
        from src.app_factory import create_app
        from src.modules.tenancy.presentation.tenant.http.tenant_gate import (
            TenantAdmissionMiddleware,
        )

        self.assertEqual(
            [m.cls for m in create_app().user_middleware],
            [ManagementTrustBoundary, TenantAdmissionMiddleware],
        )


class WiringRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_management_rejects_before_normalizing_proxy_headers(self):
        for headers, expected in (
            ([(b"host", b"manage.test"), (b"x-forwarded-for", b"10.0.0.1")], 403),
            ([(b"host", b"manage.test"), (b"host", b"manage.test")], 400),
            ([(b"host", b"public.test")], 404),
        ):
            app = ManagementTrustBoundary(
                AsyncMock(),
                enabled=True,
                management_host="manage.test",
                trusted_proxy_networks=["10.0.0.0/8"],
                allowed_core_fingerprints=[],
            )
            scope = {
                "type": "http",
                "path": "/internal/v1/status/",
                "headers": headers,
                "client": ("192.0.2.1", 123),
                "scheme": "http",
                "state": {},
            }
            send = AsyncMock()
            with patch.object(app.proxy_headers, "normalize") as normalize:
                await app(scope, AsyncMock(), send)
            normalize.assert_not_called()
            app.app.assert_not_awaited()
            self.assertEqual(send.await_args_list[0].args[0]["status"], expected)

    async def test_shared_proxy_normalization_preserves_socket_input_and_strips_headers(
        self,
    ):
        proxy = TrustedProxyHeaders(["10.0.0.0/8"])
        headers = [
            (b"x-forwarded-for", b"1.2.3.4, 192.0.2.4, 10.0.0.1"),
            (b"x-forwarded-proto", b"https"),
            (b"ssl-client-cert", b"cert"),
            (b"forwarded", b"for=other"),
            (b"host", b"tenant.test"),
        ]
        for trusted in (True, False):
            scope = {"client": ("10.0.0.2", 123), "scheme": "http", "headers": headers}
            proxy.normalize(
                scope, {key: [value] for key, value in headers}, trusted_peer=trusted
            )
            self.assertEqual(
                scope["client"], ("192.0.2.4", 0) if trusted else ("10.0.0.2", 123)
            )
            self.assertEqual(scope["scheme"], "https" if trusted else "http")
            self.assertEqual(scope["headers"], [(b"host", b"tenant.test")])

    async def test_identity_email_override_keeps_existing_dependency_contract(self):
        app = FastAPI()
        service = AsyncMock()
        app.dependency_overrides[get_email_service] = lambda: service

        @app.get("/")
        async def endpoint(email: EmailServiceDep):
            self.assertIs(email, service)
            return {"ok": True}

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://test"
        ) as client:
            self.assertEqual((await client.get("/")).json(), {"ok": True})
        service.send.assert_not_awaited()

    async def test_tenant_connection_and_one_uow_are_shared_by_all_repositories(self):
        session = Mock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        connection = object()
        app = FastAPI()
        app.state.db = Mock(
            side_effect=AssertionError("Must reuse admission connection")
        )

        async def attach_connection(request: Request):
            request.state.tenant_connection = connection

        @app.get("/", dependencies=[Depends(attach_connection)])
        async def endpoint(
            tenants: TenantsRepositoryDep,
            domains: TenantDomainsRepositoryDep,
            users: UsersRepositoryDep,
            uow: UoWDep,
        ):
            self.assertIs(tenants._session, session)
            self.assertIs(domains._session, session)
            self.assertIs(users._session, session)
            self.assertIs(uow.session, session)
            return {"ok": True}

        with patch(
            "src.modules.shared.presentation.persistence.depends.async_sessionmaker",
            return_value=lambda: session,
        ) as factory:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="https://test"
            ) as client:
                self.assertEqual((await client.get("/")).json(), {"ok": True})
        factory.assert_called_once_with(connection, expire_on_commit=False)
        session.commit.assert_awaited_once()
        session.close.assert_awaited_once()
        session.rollback.assert_not_awaited()
