"""Создание Contact на реальных tenant-схемах; только одноразовая тестовая БД."""

from dataclasses import replace
from datetime import UTC, datetime
import os
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.crm.domain.contact.aggregate import Contact
from src.modules.crm.domain.contact.value_object.identifier import ContactIdVO
from src.modules.crm.infrastructure.contact.persistence.repository import (
    SqlAlchemyContactRepository,
)
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.domain.identity_context.principal import Principal
from src.modules.shared.domain.identity_context.request_context import RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from test.crm_contact_support import contact_app

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL database."
)
class CreateContactPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant, self.other = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.actor = EntityIdVO(uuid4())
        self.now = datetime(2026, 9, 28, 12, tzinfo=UTC)
        self.identifier = uuid4()
        self.schemas = [self.naming.schema_name(t) for t in (self.tenant, self.other)]
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(CreateSchema(schema))
                await TenantMigrator().upgrade(connection, schema)
        self.context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "test", ("member",)),
            None,
            None,
            None,
        )
        self.app = contact_app(self.sessions, self.context)
        self.app.state.clock = Mock(now=Mock(return_value=self.now))
        self.app.state.uuid_generator = Mock(new=Mock(return_value=self.identifier))
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": token}

    async def asyncTearDown(self):
        await self.client.aclose()
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )
        await self.engine.dispose()

    async def create(self, **changes):
        return await self.client.post(
            "/api/console/crm/contacts",
            headers=self.headers,
            json={
                "first_name": "  Анна-Марія ",
                "last_name": " O'Neill  Smith ",
                "middle_name": " ",
                **changes,
            },
        )

    async def rows(self, tenant=None):
        async with self.sessions() as session:
            return (
                (
                    await session.execute(
                        select(ContactModel.__table__).execution_options(
                            schema_translate_map={
                                "tenant": self.naming.schema_name(tenant or self.tenant)
                            }
                        )
                    )
                )
                .mappings()
                .all()
            )

    async def test_persists_normalized_name_and_audit_before_success_response(self):
        commits = []
        original = UnitOfWork.commit

        async def commit(uow):
            # INSERT ещё не виден другой сессии до фиксации внешнего UoW.
            self.assertEqual(await self.rows(), [])
            commits.append(uow.session)
            await original(uow)

        with patch.object(UnitOfWork, "commit", commit):
            response = await self.create()
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(len(commits), 1)
        rows = await self.rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["id"], self.identifier)
        self.assertEqual(
            (row["first_name"], row["last_name"], row["middle_name"]),
            ("Анна-Марія", "O'Neill  Smith", None),
        )
        self.assertEqual((row["created_at"], row["updated_at"]), (self.now, self.now))
        self.assertEqual(
            (row["created_by"], row["updated_by"]), (self.actor.uuid, self.actor.uuid)
        )
        self.assertEqual(response.json()["id"], str(row["id"]))
        self.assertEqual(await self.rows(self.other), [])

    async def test_same_name_is_allowed_and_conflicting_id_returns_409(self):
        self.assertEqual((await self.create()).status_code, 201)
        conflict = await self.create(first_name="Other")
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.app.state.uuid_generator.new.return_value = uuid4()
        self.assertEqual((await self.create()).status_code, 201)
        rows = await self.rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["first_name"] for row in rows}, {"Анна-Марія"})

    async def test_http_uses_trusted_tenant_for_identical_ids(self):
        self.assertEqual((await self.create()).status_code, 201)
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        response = await self.create(first_name="Other")
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual((await self.rows())[0]["first_name"], "Анна-Марія")
        self.assertEqual((await self.rows(self.other))[0]["first_name"], "Other")

    async def test_failure_after_insert_rolls_back(self):
        original = SqlAlchemyContactRepository.add

        async def fail(repository, tenant_id, contact):
            await original(repository, tenant_id, contact)
            raise RuntimeError("failure after insert")

        with patch.object(SqlAlchemyContactRepository, "add", fail):
            response = await self.create()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(await self.rows(), [])

    async def test_invalid_name_does_not_write_and_legacy_null_surname_remains(self):
        async with self.engine.begin() as connection:
            await connection.execute(
                ContactModel.__table__.insert()
                .values(
                    id=self.identifier,
                    first_name="Legacy",
                    last_name=None,
                    created_by=self.actor.uuid,
                    updated_by=self.actor.uuid,
                )
                .execution_options(schema_translate_map={"tenant": self.schemas[0]})
            )
        response = await self.create(last_name=" ")
        self.assertEqual(response.status_code, 422, response.text)
        rows = await self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["first_name"], "Legacy")
        self.assertIsNone(rows[0]["last_name"])

    async def test_one_repository_and_session_can_alternate_tenants(self):
        async with UnitOfWork(self.sessions) as uow:
            repository = SqlAlchemyContactRepository(uow.session, self.naming)
            for tenant, identifier, name in (
                (self.tenant, self.identifier, "First"),
                (self.other, self.identifier, "Other"),
                (self.tenant, uuid4(), "Last"),
            ):
                contact = Contact.create(
                    contact_id=ContactIdVO(identifier),
                    first_name=name,
                    last_name="Name",
                    actor_id=self.actor,
                    now=self.now,
                )
                await repository.add(tenant, contact)
        self.assertEqual(
            {row["first_name"] for row in await self.rows()}, {"First", "Last"}
        )
        self.assertEqual(
            {row["first_name"] for row in await self.rows(self.other)}, {"Other"}
        )
