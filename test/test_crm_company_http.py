"""HTTP-контракты Company, зависимости и завершение общего UoW."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from test.crm_company_support import company_app


class CompanyHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tenant, self.actor, self.identifier = uuid4(), uuid4(), uuid4()
        self.now = datetime(2026, 10, 3, 12, tzinfo=UTC)
        self.row = dict(
            id=self.identifier,
            legal_name="Original",
            created_at=self.now,
            updated_at=self.now,
            created_by=self.actor,
            updated_by=self.actor,
        )
        self.context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "session", ("member",)),
            None,
            None,
            None,
        )
        self.result = Mock()
        self.result.mappings.return_value.one_or_none.return_value = self.row
        self.result.mappings.return_value.all.return_value = [self.row]
        self.session = SimpleNamespace(
            execute=AsyncMock(return_value=self.result),
            commit=AsyncMock(),
            rollback=AsyncMock(),
            close=AsyncMock(),
        )
        self.app = company_app(lambda: self.session, self.context)
        self.app.state.clock = Mock(now=Mock(return_value=self.now + timedelta(days=1)))
        self.app.state.uuid_generator = Mock(new=Mock(return_value=self.identifier))
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}
        self.collection = "/api/console/crm/companies"
        self.item = f"{self.collection}/{self.identifier}"

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_create_normalizes_name_and_returns_full_audit(self):
        response = await self.client.post(
            self.collection, headers=self.headers, json={"legal_name": " ACME  Group "}
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(
            response.json(),
            dict(
                id=str(self.identifier),
                legal_name="ACME  Group",
                created_at="2026-10-04T12:00:00Z",
                updated_at="2026-10-04T12:00:00Z",
                created_by=str(self.actor),
                updated_by=str(self.actor),
            ),
        )
        self.session.execute.assert_awaited_once()
        self.session.commit.assert_awaited_once()
        self.session.rollback.assert_not_awaited()

    async def test_get_and_list_return_stored_projection(self):
        get = await self.client.get(self.item)
        listing = await self.client.get(self.collection)
        self.assertEqual(get.status_code, 200, get.text)
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertEqual(listing.json(), [get.json()])
        self.assertEqual(get.json()["legal_name"], "Original")
        self.app.state.clock.now.assert_not_called()
        self.app.state.uuid_generator.new.assert_not_called()
        self.result.mappings.return_value.one_or_none.return_value = None
        self.assertEqual((await self.client.get(self.item)).status_code, 404)
        self.result.mappings.return_value.all.return_value = []
        self.assertEqual((await self.client.get(self.collection)).json(), [])

    async def test_put_patch_and_delete_are_explicit_methods(self):
        for method in ("put", "patch"):
            with self.subTest(method=method):
                response = await getattr(self.client, method)(
                    self.item, headers=self.headers, json={"legal_name": " New "}
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["legal_name"], "New")
                self.assertEqual(response.json()["updated_by"], str(self.actor))
                self.assertEqual(response.json()["created_at"], "2026-10-03T12:00:00Z")
        deleted = await self.client.delete(self.item, headers=self.headers)
        self.assertEqual(deleted.status_code, 204, deleted.text)
        self.assertEqual(deleted.content, b"")

    async def test_invalid_payloads_never_write(self):
        for method, payload in (
            ("post", {}),
            ("post", {"legal_name": None}),
            ("post", {"legal_name": " "}),
            ("post", {"legal_name": "a" * 256}),
            ("post", {"legal_name": 1}),
            ("post", {"legal_name": "A", "company_ids": []}),
            ("put", {}),
            ("put", {"legal_name": None}),
            ("patch", {}),
            ("patch", {"legal_name": None}),
            ("patch", {"legal_name": " "}),
            ("patch", {"legal_name": "A", "created_by": str(self.actor)}),
        ):
            with self.subTest(method=method, payload=payload):
                self.session.execute.reset_mock()
                url = self.collection if method == "post" else self.item
                response = await getattr(self.client, method)(
                    url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, 422, response.text)
                statements = [
                    str(call.args[0].compile())
                    for call in self.session.execute.await_args_list
                ]
                self.assertFalse(
                    any(sql.startswith(("INSERT", "UPDATE")) for sql in statements)
                )

    async def test_authentication_tenant_and_csrf_are_required(self):
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual((await self.client.get(self.collection)).status_code, 401)
        self.assertEqual(
            (
                await self.client.post(self.collection, json={"legal_name": "A"})
            ).status_code,
            401,
        )
        self.app.state.test_context = replace(
            self.context, principal=replace(self.context.principal, tenant_id=None)
        )
        self.assertEqual((await self.client.get(self.collection)).status_code, 403)
        self.app.state.test_context = self.context
        self.assertEqual(
            (
                await self.client.post(self.collection, json={"legal_name": "A"})
            ).status_code,
            403,
        )
        self.session.execute.assert_not_awaited()

    async def test_storage_and_commit_failures_do_not_return_success(self):
        self.session.execute.side_effect = RuntimeError("storage unavailable")
        self.assertEqual((await self.client.get(self.collection)).status_code, 500)
        self.session.rollback.assert_awaited_once()
        self.session.execute.side_effect = None
        self.session.rollback.reset_mock()
        self.session.commit.side_effect = RuntimeError("commit failure")
        with self.assertLogs(
            "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
            level="ERROR",
        ):
            response = await self.client.post(
                self.collection, headers=self.headers, json={"legal_name": "ACME"}
            )
        self.assertEqual(response.status_code, 500)
        self.session.rollback.assert_awaited_once()

    async def test_invalid_uuid_and_unsupported_methods(self):
        self.assertEqual(
            (await self.client.get(f"{self.collection}/invalid")).status_code, 422
        )
        self.assertEqual(
            (await self.client.request("TRACE", self.collection)).status_code, 405
        )
        self.assertEqual((await self.client.get(f"{self.item}/links")).status_code, 404)
