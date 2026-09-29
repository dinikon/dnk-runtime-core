"""Создание Contact через HTTP, DI и внешний UoW без PostgreSQL."""

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from src.config import dnk_config
from src.modules.shared.domain.identity_context.principal import Principal
from src.modules.shared.domain.identity_context.request_context import RequestContext
from test.crm_contact_support import contact_app


class CreateContactHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tenant, self.actor, self.identifier = uuid4(), uuid4(), uuid4()
        self.now = datetime(2026, 9, 28, 12, tzinfo=UTC)
        self.context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "session", ("member",)),
            None,
            None,
            None,
        )
        self.session = SimpleNamespace(
            execute=AsyncMock(),
            commit=AsyncMock(),
            rollback=AsyncMock(),
            close=AsyncMock(),
        )
        self.app = contact_app(lambda: self.session, self.context)
        self.app.state.clock = Mock(now=Mock(return_value=self.now))
        self.app.state.uuid_generator = Mock(new=Mock(return_value=self.identifier))
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}

    async def asyncTearDown(self):
        await self.client.aclose()

    async def create(self, payload=None, headers=None):
        return await self.client.post(
            "/api/console/crm/contacts",
            json=(
                payload
                if payload is not None
                else {"first_name": " A ", "last_name": " B "}
            ),
            headers=self.headers if headers is None else headers,
        )

    async def test_member_creates_contact_with_normalized_name_and_audit(self):
        response = await self.create(
            {"first_name": " A ", "last_name": " B ", "middle_name": " "}
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(
            response.json(),
            dict(
                id=str(self.identifier),
                first_name="A",
                last_name="B",
                middle_name=None,
                created_at="2026-09-28T12:00:00Z",
                updated_at="2026-09-28T12:00:00Z",
                created_by=str(self.actor),
                updated_by=str(self.actor),
            ),
        )
        self.session.execute.assert_awaited_once()
        self.session.commit.assert_awaited_once()
        self.session.rollback.assert_not_awaited()
        self.session.close.assert_awaited_once()

    async def test_missing_and_invalid_names_are_rejected(self):
        for payload in (
            {},
            {"first_name": "A"},
            {"first_name": "A", "last_name": None},
            {"first_name": " ", "last_name": "B"},
            {"first_name": "A", "last_name": 12},
            {"first_name": "A", "last_name": "b" * 256},
            {"first_name": "A", "last_name": "B", "middle_name": []},
        ):
            with self.subTest(payload=payload):
                response = await self.create(payload)
                self.assertEqual(response.status_code, 422, response.text)
        self.session.execute.assert_not_awaited()

    async def test_unknown_fields_cannot_override_context_or_add_relations(self):
        for field in (
            "id",
            "tenant_id",
            "actor_id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "phones",
            "emails",
            "company_ids",
            "expected_company_ids",
        ):
            with self.subTest(field=field):
                response = await self.create(
                    {"first_name": "A", "last_name": "B", field: str(uuid4())}
                )
                self.assertEqual(response.status_code, 422, response.text)
        self.session.execute.assert_not_awaited()

    async def test_authentication_and_tenant_are_required(self):
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual((await self.create(headers={})).status_code, 401)
        self.app.state.test_context = replace(
            self.context, principal=replace(self.context.principal, tenant_id=None)
        )
        self.assertEqual((await self.create()).status_code, 403)
        self.session.execute.assert_not_awaited()

    async def test_csrf_and_origin_are_required(self):
        for headers in (
            {},
            {"Origin": self.origin},
            {**self.headers, "Origin": "https://other.example"},
            {**self.headers, "X-CSRF-Token": "wrong"},
        ):
            with self.subTest(headers=headers):
                self.assertEqual((await self.create(headers=headers)).status_code, 403)
        self.session.execute.assert_not_awaited()

    async def test_storage_failure_rolls_back(self):
        self.session.execute.side_effect = RuntimeError("unavailable")
        self.assertEqual((await self.create()).status_code, 500)
        self.session.commit.assert_not_awaited()
        self.session.rollback.assert_awaited_once()
        self.session.close.assert_awaited_once()

    async def test_unexpected_integrity_error_is_not_a_conflict(self):
        self.session.execute.side_effect = IntegrityError(
            None, None, Exception("unexpected constraint")
        )
        self.assertEqual((await self.create()).status_code, 500)
        self.session.rollback.assert_awaited_once()

    async def test_commit_failure_never_returns_created(self):
        self.session.commit.side_effect = RuntimeError("commit failure")
        with self.assertLogs(
            "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
            level="ERROR",
        ):
            response = await self.create()
        self.assertEqual(response.status_code, 500)
        self.session.rollback.assert_awaited_once()
        self.session.close.assert_awaited_once()
