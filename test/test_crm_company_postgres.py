"""Company CRUD в tenant-схемах одноразовой PostgreSQL базы."""

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
from src.modules.crm.infrastructure.company.persistence.repository import (
    SqlAlchemyCompanyRepository,
)
from src.modules.crm.infrastructure.persistence.models.company import CompanyModel
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel
from src.modules.crm.infrastructure.persistence.models.contact_company import (
    ContactCompanyModel,
)
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from test.crm_company_support import company_app

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL database."
)
class CompanyPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant, self.other = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.actor = EntityIdVO(uuid4())
        self.identifier = uuid4()
        self.now = datetime(2026, 10, 3, tzinfo=UTC)
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
        self.app = company_app(self.sessions, self.context, scoped_connection=True)
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
        self.collection = "/api/console/crm/companies"
        self.item = f"{self.collection}/{self.identifier}"

    async def asyncTearDown(self):
        await self.client.aclose()
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )
        await self.engine.dispose()

    async def rows(self, model, tenant=None):
        schema = self.naming.schema_name(tenant or self.tenant)
        async with self.sessions() as session:
            result = await session.execute(
                select(model.__table__).execution_options(
                    schema_translate_map={"tenant": schema}
                )
            )
            return result.mappings().all()

    async def create(self, legal_name=" ACME  Group "):
        return await self.client.post(
            self.collection, headers=self.headers, json={"legal_name": legal_name}
        )

    async def test_crud_isolation_duplicate_name_and_cascade(self):
        created = await self.create()
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["legal_name"], "ACME  Group")
        row = (await self.rows(CompanyModel))[0]
        self.assertEqual(row["id"], self.identifier)
        self.assertEqual((row["created_at"], row["updated_at"]), (self.now,) * 2)
        self.assertEqual((row["created_by"], row["updated_by"]), (self.actor.uuid,) * 2)
        self.assertEqual(await self.rows(CompanyModel, self.other), [])

        self.app.state.uuid_generator.new.return_value = uuid4()
        self.assertEqual((await self.create()).status_code, 201)
        self.assertEqual(len(await self.rows(CompanyModel)), 2)
        self.app.state.uuid_generator.new.return_value = self.identifier
        self.assertEqual((await self.create("Other")).status_code, 409)

        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        self.assertEqual((await self.client.get(self.item)).status_code, 404)
        self.assertEqual((await self.create("Other")).status_code, 201)
        self.assertEqual(
            (await self.client.get(self.item)).json()["legal_name"], "Other"
        )
        self.app.state.test_context = self.context

        updated = await self.client.patch(
            self.item, headers=self.headers, json={"legal_name": " Renamed "}
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual((await self.rows(CompanyModel))[0]["legal_name"], "Renamed")
        self.assertEqual(
            (await self.rows(CompanyModel, self.other))[0]["legal_name"], "Other"
        )
        replaced = await self.client.put(
            self.item, headers=self.headers, json={"legal_name": " Final "}
        )
        self.assertEqual(replaced.status_code, 200, replaced.text)
        self.assertEqual(replaced.json()["legal_name"], "Final")

        contact_id = uuid4()
        schema = self.schemas[0]
        async with self.engine.begin() as connection:
            await connection.execute(
                ContactModel.__table__.insert()
                .values(
                    id=contact_id,
                    first_name="Person",
                    last_name="Name",
                    created_by=self.actor.uuid,
                    updated_by=self.actor.uuid,
                )
                .execution_options(schema_translate_map={"tenant": schema})
            )
            await connection.execute(
                ContactCompanyModel.__table__.insert()
                .values(contact_id=contact_id, company_id=self.identifier)
                .execution_options(schema_translate_map={"tenant": schema})
            )
        self.assertEqual(len(await self.rows(ContactCompanyModel)), 1)
        deleted = await self.client.delete(self.item, headers=self.headers)
        self.assertEqual(deleted.status_code, 204, deleted.text)
        self.assertEqual(await self.rows(ContactCompanyModel), [])
        self.assertEqual(len(await self.rows(ContactModel)), 1)
        self.assertEqual((await self.client.get(self.item)).status_code, 404)
        self.assertEqual(len(await self.rows(CompanyModel, self.other)), 1)

    async def test_failure_after_write_rolls_back(self):
        original = SqlAlchemyCompanyRepository.add

        async def fail(repository, company):
            await original(repository, company)
            raise RuntimeError("failure after insert")

        with patch.object(SqlAlchemyCompanyRepository, "add", fail):
            response = await self.create()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(await self.rows(CompanyModel), [])
