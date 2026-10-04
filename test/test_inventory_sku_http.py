"""SKU HTTP с настоящими DI, authentication, authorization, CSRF и UoW."""

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from test.inventory_sku_support import sku_app


class SkuHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tenant, self.actor, self.identifier = uuid4(), uuid4(), uuid4()
        self.now = datetime(2026, 10, 4, tzinfo=UTC)
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
        self.app = sku_app(lambda: self.session, self.context)
        self.app.state.clock = Mock(now=Mock(return_value=self.now))
        self.app.state.uuid_generator = Mock(new=Mock(return_value=self.identifier))
        self.authorization = Mock(can=AsyncMock(return_value=True))
        self.app.state.authorization_service = self.authorization
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        self.collection = "/api/console/inventory/skus"
        self.item = f"{self.collection}/{self.identifier}"
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}

    async def asyncTearDown(self):
        await self.client.aclose()

    async def create(self, payload=None, headers=None):
        return await self.client.post(
            self.collection,
            json=(
                payload
                if payload is not None
                else {"code": " OMEGA-100 ", "title": " Omega 100 "}
            ),
            headers=self.headers if headers is None else headers,
        )

    async def test_create_returns_normalized_audit_and_commits(self):
        response = await self.create()
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(
            response.json(),
            dict(
                id=str(self.identifier),
                code="OMEGA-100",
                title="Omega 100",
                created_at="2026-10-04T00:00:00Z",
                updated_at="2026-10-04T00:00:00Z",
                created_by=str(self.actor),
                updated_by=str(self.actor),
            ),
        )
        self.authorization.can.assert_awaited_once_with(
            user_id=self.actor,
            tenant_id=self.tenant,
            action="create",
            resource_type="inventory.sku",
        )
        self.session.execute.assert_awaited_once()
        self.session.commit.assert_awaited_once()
        self.session.rollback.assert_not_awaited()
        self.session.close.assert_awaited_once()

    async def test_invalid_fields_and_context_injection_never_write(self):
        invalid = [
            {},
            {"code": None, "title": "Title"},
            {"code": 12, "title": "Title"},
            {"code": " ", "title": "Title"},
            {"code": "A", "title": " "},
            {"code": "a" * 129, "title": "Title"},
            {"code": "A\nB", "title": "Title"},
        ]
        invalid += [
            {"code": "A", "title": "Title", field: str(uuid4())}
            for field in (
                "id",
                "tenant_id",
                "actor_id",
                "created_by",
                "updated_by",
                "stock",
            )
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                self.assertEqual((await self.create(payload)).status_code, 422)
        self.session.execute.assert_not_awaited()

    async def test_auth_tenant_and_csrf_are_required(self):
        self.app.state.test_context = replace(self.context, principal=None)
        for method, path in (
            ("get", self.collection),
            ("get", self.item),
            ("post", self.collection),
        ):
            self.assertEqual(
                (
                    await self.client.request(
                        method,
                        path,
                        json=(
                            {"code": "A", "title": "Title"}
                            if method == "post"
                            else None
                        ),
                    )
                ).status_code,
                401,
            )
        self.app.state.test_context = replace(
            self.context, principal=replace(self.context.principal, tenant_id=None)
        )
        self.assertEqual((await self.create()).status_code, 403)
        self.app.state.test_context = self.context
        for headers in (
            {},
            {"Origin": self.origin},
            {**self.headers, "Origin": "https://other.example"},
            {**self.headers, "X-CSRF-Token": "wrong"},
        ):
            self.assertEqual((await self.create(headers=headers)).status_code, 403)
        self.session.execute.assert_not_awaited()

    async def test_authorization_denial_never_reads_or_writes(self):
        self.authorization.can.return_value = False
        self.assertEqual((await self.create()).status_code, 403)
        self.assertEqual((await self.client.get(self.item)).status_code, 403)
        self.assertEqual((await self.client.get(self.collection)).status_code, 403)
        self.session.execute.assert_not_awaited()

    async def test_named_duplicate_code_is_conflict_and_rolls_back(self):
        cause = Exception("duplicate")
        cause.constraint_name = "uq_skus_code"
        original = Exception("duplicate")
        original.sqlstate = "23505"
        original.__cause__ = cause
        self.session.execute.side_effect = IntegrityError(None, None, original)
        response = await self.create()
        self.assertEqual(response.status_code, 409, response.text)
        self.session.rollback.assert_awaited_once()
        self.session.commit.assert_not_awaited()

    async def test_unknown_integrity_and_commit_failures_never_return_created(self):
        self.session.execute.side_effect = IntegrityError(
            None, None, Exception("unexpected")
        )
        self.assertEqual((await self.create()).status_code, 500)
        self.session.execute.side_effect = None
        self.session.commit.side_effect = RuntimeError("commit failure")
        with self.assertLogs(
            "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
            level="ERROR",
        ):
            self.assertEqual((await self.create()).status_code, 500)

    async def test_get_missing_and_paginated_projection(self):
        result = Mock()
        self.session.execute.return_value = result
        result.mappings.return_value.one_or_none.return_value = None
        self.assertEqual((await self.client.get(self.item)).status_code, 404)
        row = dict(
            id=self.identifier,
            code="A",
            title="Title",
            created_at=self.now,
            updated_at=self.now,
            created_by=self.actor,
            updated_by=self.actor,
        )
        result.mappings.return_value.one_or_none.return_value = row
        result.mappings.return_value.all.return_value = [row]
        self.assertEqual((await self.client.get(self.item)).json()["code"], "A")
        response = await self.client.get(
            self.collection, params={"limit": 5, "offset": 10}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()[0]["id"], str(self.identifier))
        parameters = self.session.execute.await_args.args[0].compile().params
        self.assertEqual(set(parameters.values()), {5, 10})
        self.session.execute.reset_mock()
        for params in ({"limit": 0}, {"limit": 201}, {"offset": -1}, {"limit": "abc"}):
            self.assertEqual(
                (await self.client.get(self.collection, params=params)).status_code, 422
            )
        self.session.execute.assert_not_awaited()
