"""Два направления HTTP одной связи Contact–Company."""

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.crm.presentation.company.router import router as company_router
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from test.crm_contact_support import contact_app


class ContactCompanyHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tenant, self.actor, self.contact_id, self.company_id = (
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
        )
        self.now = datetime(2026, 10, 4, tzinfo=UTC)
        self.context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "session", ("member",)),
            None,
            None,
            None,
        )
        self.result = Mock()
        self.result.scalar_one_or_none.return_value = self.contact_id
        self.session = SimpleNamespace(
            execute=AsyncMock(return_value=self.result),
            commit=AsyncMock(),
            rollback=AsyncMock(),
            close=AsyncMock(),
        )
        self.app = contact_app(lambda: self.session, self.context)
        self.app.include_router(company_router, prefix="/api/console")
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}
        self.contact_url = (
            f"/api/console/crm/contacts/{self.contact_id}/companies/{self.company_id}"
        )
        self.company_url = (
            f"/api/console/crm/companies/{self.company_id}/contacts/{self.contact_id}"
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_both_urls_link_and_unlink_the_same_pair(self):
        for method, url in (
            ("put", self.contact_url),
            ("put", self.company_url),
            ("delete", self.contact_url),
            ("delete", self.company_url),
        ):
            with self.subTest(method=method, url=url):
                self.session.execute.reset_mock()
                self.session.commit.reset_mock()
                response = await getattr(self.client, method)(url, headers=self.headers)
                self.assertEqual(response.status_code, 204, response.text)
                self.assertEqual(response.content, b"")
                self.assertEqual(self.session.execute.await_count, 3)
                sql = str(self.session.execute.await_args.args[0].compile())
                self.assertIn("contact_companies", sql)
                self.session.commit.assert_awaited_once()
                self.session.rollback.assert_not_awaited()

    async def test_lists_are_single_query_and_return_complete_projection(self):
        company = dict(
            owner_id=self.contact_id,
            id=self.company_id,
            legal_name="ACME",
            created_at=self.now,
            updated_at=self.now,
            created_by=self.actor,
            updated_by=self.actor,
        )
        contact = dict(
            owner_id=self.company_id,
            id=self.contact_id,
            first_name="Jane",
            last_name="Doe",
            middle_name=None,
            created_at=self.now,
            updated_at=self.now,
            created_by=self.actor,
            updated_by=self.actor,
        )
        for url, row, field in (
            (
                f"/api/console/crm/contacts/{self.contact_id}/companies",
                company,
                "legal_name",
            ),
            (
                f"/api/console/crm/companies/{self.company_id}/contacts",
                contact,
                "first_name",
            ),
        ):
            with self.subTest(url=url):
                self.result.mappings.return_value.all.return_value = [row]
                self.session.execute.reset_mock()
                response = await self.client.get(url)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()[0][field], row[field])
                self.assertEqual(response.json()[0]["id"], str(row["id"]))
                self.assertEqual(len(response.json()[0]), len(row) - 1)
                self.session.execute.assert_awaited_once()
                self.result.mappings.return_value.all.return_value = [
                    {**row, "id": None}
                ]
                self.assertEqual((await self.client.get(url)).json(), [])
                self.result.mappings.return_value.all.return_value = []
                missing = await self.client.get(url)
                self.assertEqual(missing.status_code, 404, missing.text)

    async def test_missing_parent_and_invalid_uuid(self):
        self.result.scalar_one_or_none.return_value = None
        response = await self.client.put(self.contact_url, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Contact not found."})
        self.assertEqual(self.session.execute.await_count, 1)
        self.session.execute.reset_mock()
        self.result.scalar_one_or_none.side_effect = [self.contact_id, None]
        response = await self.client.delete(self.company_url, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Company not found."})
        self.assertEqual(self.session.execute.await_count, 2)
        self.session.execute.reset_mock()
        bad = await self.client.put(
            self.contact_url.replace(str(self.company_id), "invalid"),
            headers=self.headers,
        )
        self.assertEqual(bad.status_code, 422)
        self.session.execute.assert_not_awaited()

    async def test_authentication_tenant_and_csrf(self):
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual(
            (
                await self.client.get(
                    f"/api/console/crm/contacts/{self.contact_id}/companies"
                )
            ).status_code,
            401,
        )
        self.assertEqual((await self.client.put(self.company_url)).status_code, 401)
        self.app.state.test_context = replace(
            self.context, principal=replace(self.context.principal, tenant_id=None)
        )
        self.assertEqual(
            (await self.client.put(self.contact_url, headers=self.headers)).status_code,
            403,
        )
        self.app.state.test_context = self.context
        self.assertEqual((await self.client.put(self.contact_url)).status_code, 403)
        self.session.execute.assert_not_awaited()

    async def test_commit_failure_and_storage_failure_never_return_204(self):
        self.session.commit.side_effect = RuntimeError("commit failure")
        with self.assertLogs(
            "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
            level="ERROR",
        ):
            response = await self.client.put(self.contact_url, headers=self.headers)
        self.assertEqual(response.status_code, 500)
        self.session.rollback.assert_awaited_once()
        self.session.commit.side_effect = None
        self.session.rollback.reset_mock()
        self.session.execute.side_effect = RuntimeError("storage failure")
        response = await self.client.delete(self.company_url, headers=self.headers)
        self.assertEqual(response.status_code, 500)
        self.session.rollback.assert_awaited_once()
