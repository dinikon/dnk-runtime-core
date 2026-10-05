"""HTTP-контракт выбора локалей: auth, CSRF, ошибки и явные схемы."""

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.tenancy.application.tenant_locale.port.query_repository import (
    TenantLocaleRecord,
)
from src.modules.tenancy.domain.tenant_locale.error import (
    TenantLocaleAlreadySelectedError,
)
from src.modules.tenancy.presentation.tenant_locale.depends import (
    get_tenant_locale_query_repository,
)
from src.modules.tenancy.presentation.tenant_locale.depends import (
    get_tenant_locale_repository,
)
from test.tenant_locale_support import tenant_locale_app


class MemoryTenantLocaleRepository:
    def __init__(self):
        self.items = {}

    async def add(self, locale):
        if locale.code.value in self.items:
            raise TenantLocaleAlreadySelectedError("Locale is already selected.")
        self.items[locale.code.value] = locale

    async def remove(self, code):
        return self.items.pop(code.value, None) is not None

    async def list_all(self):
        return [
            TenantLocaleRecord(
                code, self.items[code].created_at, self.items[code].created_by.uuid
            )
            for code in sorted(self.items)
        ]

    async def contains(self, code):
        return code.value in self.items


class TenantLocaleHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tenant, self.actor = uuid4(), uuid4()
        self.context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "session", ("member",)),
            None,
            None,
            None,
        )
        self.repository = MemoryTenantLocaleRepository()
        self.app = tenant_locale_app(None, self.context)
        self.app.dependency_overrides[get_tenant_locale_repository] = (
            lambda: self.repository
        )
        self.app.dependency_overrides[get_tenant_locale_query_repository] = (
            lambda: self.repository
        )
        self.app.state.clock = Mock(
            now=Mock(return_value=datetime(2026, 10, 5, tzinfo=UTC))
        )
        self.authorization = Mock(can=AsyncMock(return_value=True))
        self.app.state.authorization_service = self.authorization
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        self.path = "/api/console/tenants/locales"
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_list_add_and_remove(self):
        available = await self.client.get(f"{self.path}/available")
        self.assertEqual(available.status_code, 200)
        self.assertEqual([item["code"] for item in available.json()], ["uk", "en"])
        self.assertEqual((await self.client.get(self.path)).json(), [])

        created = await self.client.post(
            self.path, json={"code": "uk"}, headers=self.headers
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(
            created.json(),
            {
                "code": "uk",
                "created_at": "2026-10-05T00:00:00Z",
                "created_by": str(self.actor),
            },
        )
        self.assertEqual((await self.client.get(self.path)).json(), [created.json()])
        self.assertEqual(
            (
                await self.client.post(
                    self.path, json={"code": "uk"}, headers=self.headers
                )
            ).status_code,
            409,
        )
        self.assertEqual(
            (
                await self.client.delete(f"{self.path}/uk", headers=self.headers)
            ).status_code,
            204,
        )
        self.assertEqual((await self.client.get(self.path)).json(), [])
        self.assertEqual(
            (
                await self.client.delete(f"{self.path}/uk", headers=self.headers)
            ).status_code,
            404,
        )

    async def test_invalid_codes_and_extra_fields_never_write(self):
        for payload in (
            {"code": "de"},
            {"code": " uk "},
            {"code": 4},
            {"code": "uk", "tenant_id": str(self.tenant)},
        ):
            with self.subTest(payload=payload):
                response = await self.client.post(
                    self.path, json=payload, headers=self.headers
                )
                self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.repository.items, {})
        self.assertEqual(
            (
                await self.client.delete(f"{self.path}/de", headers=self.headers)
            ).status_code,
            422,
        )

    async def test_auth_tenant_authorization_and_csrf(self):
        self.app.state.test_context = replace(self.context, principal=None)
        for method, path in (
            ("GET", self.path),
            ("GET", f"{self.path}/available"),
            ("POST", self.path),
            ("DELETE", f"{self.path}/uk"),
        ):
            with self.subTest(method=method, path=path):
                response = await self.client.request(
                    method,
                    path,
                    json={"code": "uk"} if method == "POST" else None,
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 401, response.text)
        self.app.state.test_context = replace(
            self.context, principal=replace(self.context.principal, tenant_id=None)
        )
        self.assertEqual((await self.client.get(self.path)).status_code, 403)
        self.app.state.test_context = self.context
        self.authorization.can.return_value = False
        self.assertEqual((await self.client.get(self.path)).status_code, 403)
        self.assertEqual(
            (
                await self.client.post(
                    self.path, json={"code": "uk"}, headers=self.headers
                )
            ).status_code,
            403,
        )
        self.authorization.can.return_value = True
        self.assertEqual(
            (await self.client.post(self.path, json={"code": "uk"})).status_code, 403
        )
        self.assertEqual((await self.client.delete(f"{self.path}/uk")).status_code, 403)
        self.assertEqual(self.repository.items, {})

    async def test_commit_failure_cannot_return_created(self):
        session = SimpleNamespace(
            execute=AsyncMock(),
            commit=AsyncMock(side_effect=RuntimeError("commit failed")),
            rollback=AsyncMock(),
            close=AsyncMock(),
        )
        self.app.state.db = lambda: session
        del self.app.dependency_overrides[get_tenant_locale_repository]

        response = await self.client.post(
            self.path, json={"code": "uk"}, headers=self.headers
        )
        self.assertEqual(response.status_code, 500)
        session.execute.assert_awaited_once()
        session.commit.assert_awaited_once()
        session.rollback.assert_awaited_once()
        session.close.assert_awaited_once()
