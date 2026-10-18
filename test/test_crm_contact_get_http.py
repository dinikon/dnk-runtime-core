"""HTTP-контракт чтения Contact с реальными Query Handler, DI и UoW."""

from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from test.crm_contact_support import contact_app
from test.test_crm_contact_get import contact_row


class GetContactHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.row = contact_row()
        self.context = RequestContext(
            Principal(str(uuid4()), str(uuid4()), "session", ("member",)),
            None,
            None,
            None,
        )
        self.result = Mock()
        self.result.mappings.return_value.one_or_none.return_value = self.row
        self.session = SimpleNamespace(
            execute=AsyncMock(return_value=self.result),
            commit=AsyncMock(),
            rollback=AsyncMock(),
            close=AsyncMock(),
        )
        self.app = contact_app(lambda: self.session, self.context)
        self.app.state.uuid_generator = Mock(
            new=Mock(side_effect=AssertionError("No UUID generation on read"))
        )
        self.app.state.clock = Mock(
            now=Mock(side_effect=AssertionError("No clock on read"))
        )
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url="https://tenant.example",
        )
        self.url = f"/api/console/crm/contacts/{self.row['id']}"

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_member_reads_all_fields_without_csrf_or_cookies(self):
        response = await self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.text)
        expected = {
            key: (
                value.isoformat().replace("+00:00", "Z")
                if key.endswith("_at")
                else str(value) if key in {"id", "created_by", "updated_by"} else value
            )
            for key, value in self.row.items()
        }
        self.assertEqual(response.json(), expected)
        self.session.execute.assert_awaited_once()
        self.session.commit.assert_awaited_once()
        self.session.close.assert_awaited_once()
        self.app.state.clock.now.assert_not_called()
        self.app.state.uuid_generator.new.assert_not_called()

    async def test_not_found_returns_404(self):
        self.result.mappings.return_value.one_or_none.return_value = None
        response = await self.client.get(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Contact not found."})

    async def test_invalid_uuid_returns_422_without_query(self):
        response = await self.client.get("/api/console/crm/contacts/invalid-uuid")
        self.assertEqual(response.status_code, 422)
        self.session.execute.assert_not_awaited()

    async def test_authentication_and_tenant_required(self):
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual((await self.client.get(self.url)).status_code, 401)
        self.app.state.test_context = replace(
            self.context, principal=replace(self.context.principal, tenant_id=None)
        )
        self.assertEqual((await self.client.get(self.url)).status_code, 403)
        self.session.execute.assert_not_awaited()

    async def test_storage_error_rolls_back_and_closes_session(self):
        self.session.execute.side_effect = RuntimeError("unavailable")
        self.assertEqual((await self.client.get(self.url)).status_code, 500)
        self.session.rollback.assert_awaited_once()
        self.session.close.assert_awaited_once()

    async def test_uow_failure_cannot_return_success(self):
        self.session.commit.side_effect = RuntimeError("commit failure")
        with self.assertLogs(
            "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
            level="ERROR",
        ):
            response = await self.client.get(self.url)
        self.assertEqual(response.status_code, 500)
        self.session.rollback.assert_awaited_once()
        self.session.close.assert_awaited_once()
