"""Контракт list/PUT/PATCH/DELETE и доменные правила Contact."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import RowMapping

from src.config import dnk_config
from src.modules.crm.application.contact.command.update_contact.command import (
    UpdateContactCommand,
)
from src.modules.crm.application.contact.command.update_contact.handler import (
    UpdateContactHandler,
)
from src.modules.crm.domain.contact.aggregate import ContactEntity
from src.modules.crm.domain.contact.error import InvalidContactNameError
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.domain.contact.value_object.name import ContactNameVO
from src.modules.crm.infrastructure.contact.persistence.mapper import ContactMapper
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from test.crm_contact_support import contact_app


class UpdateContactHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_storage_mapper_restores_contact_name_vo(self):
        now = datetime(2026, 10, 1, tzinfo=UTC)
        actor = uuid4()
        row = dict(
            id=uuid4(),
            first_name="Jane",
            last_name="Doe",
            middle_name=None,
            created_at=now,
            updated_at=now,
            created_by=actor,
            updated_by=actor,
        )
        contact = ContactMapper.to_entity(cast(RowMapping, row))
        self.assertIsInstance(contact.name, ContactNameVO)
        without_surname = ContactMapper.to_entity(
            cast(RowMapping, {**row, "last_name": None})
        )
        self.assertIsNone(without_surname.name.last_name)
        with self.assertRaises(InvalidContactNameError):
            ContactMapper.to_entity(cast(RowMapping, {**row, "first_name": " "}))

    async def test_patch_updates_valid_name_and_audit_once(self):
        old, now = datetime(2026, 9, 1, tzinfo=UTC), datetime(2026, 10, 1, tzinfo=UTC)
        actor, next_actor = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        contact = ContactEntity.create(
            contact_id=ContactIdVO(uuid4()),
            first_name=" Jane ",
            last_name=" Smith ",
            actor_id=actor,
            now=old,
        )
        repository = Mock(
            get_for_update=AsyncMock(return_value=contact), save=AsyncMock()
        )
        clock = Mock(now=Mock(return_value=now))
        handler = UpdateContactHandler(repository, clock)
        command = UpdateContactCommand(
            contact.id, next_actor, frozenset({"last_name"}), last_name=" Doe "
        )
        result = await handler.execute(command)
        self.assertEqual((result.first_name, result.last_name), ("Jane", "Doe"))
        self.assertEqual((result.created_at, result.updated_at), (old, now))
        self.assertEqual(
            (result.created_by, result.updated_by), (actor.uuid, next_actor.uuid)
        )
        repository.save.assert_awaited_once_with(contact)
        await handler.execute(command)
        repository.save.assert_awaited_once()

    async def test_invalid_patch_does_not_save(self):
        actor = EntityIdVO(uuid4())
        now = datetime(2026, 10, 1, tzinfo=UTC)
        contact = ContactEntity.create(
            contact_id=ContactIdVO(uuid4()),
            first_name="Jane",
            last_name="Doe",
            actor_id=actor,
            now=now,
        )
        repository = Mock(
            get_for_update=AsyncMock(return_value=contact), save=AsyncMock()
        )
        handler = UpdateContactHandler(repository, Mock(now=Mock(return_value=now)))
        with self.assertRaises(InvalidContactNameError):
            await handler.execute(
                UpdateContactCommand(
                    contact.id,
                    actor,
                    frozenset({"first_name"}),
                    first_name=None,
                )
            )
        repository.save.assert_not_awaited()
        self.assertEqual(contact.name.first_name, "Jane")


class ContactMethodsHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tenant, self.actor, self.identifier = uuid4(), uuid4(), uuid4()
        self.now = datetime(2026, 10, 3, tzinfo=UTC)
        self.row = dict(
            id=self.identifier,
            first_name="Jane",
            last_name="Doe",
            middle_name=None,
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
        self.app = contact_app(lambda: self.session, self.context)
        self.app.state.clock = Mock(now=Mock(return_value=self.now + timedelta(days=1)))
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}
        self.url = f"/api/console/crm/contacts/{self.identifier}"
        self.session.execute.reset_mock()
        self.session.commit.reset_mock()

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_patch_schema_has_optional_nonnullable_first_name(self):
        schema = self.app.openapi()["components"]["schemas"]["PatchContactRequest"]
        self.assertNotIn("first_name", schema.get("required", []))
        self.assertEqual(schema["properties"]["first_name"]["type"], "string")

    async def test_list_returns_all_without_clock_or_csrf(self):
        response = await self.client.get("/api/console/crm/contacts")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()[0]["id"], str(self.identifier))
        statement = self.session.execute.await_args.args[0]
        self.assertIn("ORDER BY", str(statement))
        self.assertNotIn("LIMIT", str(statement))
        self.app.state.clock.now.assert_not_called()

    async def test_list_returns_empty_array(self):
        self.result.mappings.return_value.all.return_value = []
        response = await self.client.get("/api/console/crm/contacts")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), [])

    async def test_put_replaces_full_name_and_patch_preserves_omitted_fields(self):
        response = await self.client.put(
            self.url,
            headers=self.headers,
            json={"first_name": " Ann ", "last_name": " Smith ", "middle_name": " "},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            (
                response.json()["first_name"],
                response.json()["last_name"],
                response.json()["middle_name"],
            ),
            ("Ann", "Smith", None),
        )
        self.assertEqual(response.json()["updated_by"], str(self.actor))
        self.assertEqual(self.session.execute.await_count, 2)
        self.session.execute.reset_mock()
        response = await self.client.patch(
            self.url,
            headers=self.headers,
            json={"middle_name": " Marie "},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["first_name"], "Jane")
        self.assertEqual(response.json()["middle_name"], "Marie")
        self.assertEqual(self.session.execute.await_count, 2)

    async def test_put_and_patch_can_clear_optional_surname(self):
        put = await self.client.put(
            self.url,
            headers=self.headers,
            json={"first_name": " Solo "},
        )
        self.assertEqual(put.status_code, 200, put.text)
        self.assertEqual(put.json()["first_name"], "Solo")
        self.assertIsNone(put.json()["last_name"])
        patch = await self.client.patch(
            self.url,
            headers=self.headers,
            json={"last_name": None},
        )
        self.assertEqual(patch.status_code, 200, patch.text)
        self.assertEqual(patch.json()["first_name"], "Jane")
        self.assertIsNone(patch.json()["last_name"])

    async def test_invalid_bodies_and_csrf_are_rejected(self):
        for method, payload in (
            ("put", {}),
            ("put", {"first_name": "Jane", "last_name": "Doe", "id": str(uuid4())}),
            ("patch", {}),
            ("patch", {"first_name": None}),
            ("patch", {"first_name": " "}),
        ):
            with self.subTest(method=method, payload=payload):
                response = await getattr(self.client, method)(
                    self.url,
                    headers=self.headers,
                    json=payload,
                )
                self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual((await self.client.delete(self.url)).status_code, 403)
        self.session.execute.assert_awaited()

    async def test_delete_returns_204_and_missing_returns_404(self):
        response = await self.client.delete(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.session.execute.await_count, 3)
        self.result.mappings.return_value.one_or_none.return_value = None
        response = await self.client.delete(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        for method, payload in (
            ("put", {"first_name": "A", "last_name": "B"}),
            ("patch", {"first_name": "A"}),
        ):
            with self.subTest(method=method):
                response = await getattr(self.client, method)(
                    self.url,
                    headers=self.headers,
                    json=payload,
                )
                self.assertEqual(response.status_code, 404)

    async def test_auth_tenant_and_commit_failure(self):
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual(
            (await self.client.get("/api/console/crm/contacts")).status_code, 401
        )
        self.app.state.test_context = replace(
            self.context, principal=replace(self.context.principal, tenant_id=None)
        )
        self.assertEqual(
            (await self.client.get("/api/console/crm/contacts")).status_code, 403
        )
        self.app.state.test_context = self.context
        self.session.rollback.reset_mock()
        self.session.commit.side_effect = RuntimeError("commit failure")
        with self.assertLogs(
            "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
            level="ERROR",
        ):
            response = await self.client.delete(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 500)
        self.session.rollback.assert_awaited_once()
