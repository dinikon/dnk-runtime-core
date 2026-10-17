"""Связи Contact–Company в одноразовой PostgreSQL базе с tenant-схемами."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.crm.infrastructure.contact.persistence.company_link_repository import (
    SqlAlchemyCompanyLinkRepository,
)
from src.modules.crm.infrastructure.persistence.models.company import CompanyModel
from src.modules.crm.infrastructure.persistence.models.contact import ContactModel
from src.modules.crm.infrastructure.persistence.models.contact_company import (
    ContactCompanyModel,
)
from src.modules.crm.presentation.company.router import router as company_router
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from test.crm_contact_support import contact_app

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL database."
)
class ContactCompanyPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant, self.other = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.actor = EntityIdVO(uuid4())
        self.contact_id, self.company_id = uuid4(), uuid4()
        self.now = datetime(2026, 10, 4, tzinfo=UTC)
        self.schemas = [
            self.naming.schema_name(item) for item in (self.tenant, self.other)
        ]
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
        self.app = contact_app(self.sessions, self.context, scoped_connection=True)
        self.app.include_router(company_router, prefix="/api/console")
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": token}
        self.contact_item = f"/api/console/crm/contacts/{self.contact_id}"
        self.company_item = f"/api/console/crm/companies/{self.company_id}"
        self.contact_link = f"{self.contact_item}/companies/{self.company_id}"
        self.company_link = f"{self.company_item}/contacts/{self.contact_id}"
        for tenant in (self.tenant, self.other):
            await self.seed(tenant)

    async def asyncTearDown(self):
        await self.client.aclose()
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )
        await self.engine.dispose()

    async def seed(self, tenant):
        schema = self.naming.schema_name(tenant)
        async with self.engine.begin() as connection:
            await connection.execute(
                ContactModel.__table__.insert()
                .values(
                    id=self.contact_id,
                    first_name="Jane",
                    last_name="Doe",
                    created_at=self.now,
                    updated_at=self.now,
                    created_by=self.actor.uuid,
                    updated_by=self.actor.uuid,
                )
                .execution_options(schema_translate_map={"tenant": schema})
            )
            await connection.execute(
                CompanyModel.__table__.insert()
                .values(
                    id=self.company_id,
                    legal_name="ACME",
                    created_at=self.now,
                    updated_at=self.now,
                    created_by=self.actor.uuid,
                    updated_by=self.actor.uuid,
                )
                .execution_options(schema_translate_map={"tenant": schema})
            )

    async def links(self, tenant=None):
        schema = self.naming.schema_name(tenant or self.tenant)
        async with self.sessions() as session:
            result = await session.execute(
                select(ContactCompanyModel.__table__).execution_options(
                    schema_translate_map={"tenant": schema}
                )
            )
            return result.mappings().all()

    async def test_both_directions_are_one_idempotent_tenant_link(self):
        contact_before = (await self.client.get(self.contact_item)).json()
        company_before = (await self.client.get(self.company_item)).json()
        self.assertEqual(
            (await self.client.get(f"{self.contact_item}/companies")).json(), []
        )
        self.assertEqual(
            (await self.client.get(f"{self.company_item}/contacts")).json(), []
        )
        responses = await asyncio.gather(
            self.client.put(self.contact_link, headers=self.headers),
            self.client.put(self.company_link, headers=self.headers),
        )
        self.assertEqual([item.status_code for item in responses], [204, 204])
        self.assertEqual(len(await self.links()), 1)
        self.assertEqual(await self.links(self.other), [])
        self.assertEqual(
            (await self.client.get(self.contact_item)).json(), contact_before
        )
        self.assertEqual(
            (await self.client.get(self.company_item)).json(), company_before
        )
        self.assertEqual(
            (await self.client.get(f"{self.contact_item}/companies")).json()[0][
                "legal_name"
            ],
            "ACME",
        )
        self.assertEqual(
            (await self.client.get(f"{self.company_item}/contacts")).json()[0][
                "first_name"
            ],
            "Jane",
        )
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        self.assertEqual(
            (
                await self.client.put(self.company_link, headers=self.headers)
            ).status_code,
            204,
        )
        self.assertEqual(len(await self.links(self.other)), 1)
        self.assertEqual(
            (
                await self.client.delete(self.contact_link, headers=self.headers)
            ).status_code,
            204,
        )
        self.assertEqual(await self.links(self.other), [])
        self.assertEqual(len(await self.links()), 1)
        self.app.state.test_context = self.context
        self.assertEqual(
            (
                await self.client.delete(self.company_link, headers=self.headers)
            ).status_code,
            204,
        )
        self.assertEqual(
            (
                await self.client.delete(self.contact_link, headers=self.headers)
            ).status_code,
            204,
        )
        self.assertEqual(await self.links(), [])

    async def test_parent_errors_rollback_and_cascade(self):
        missing_contact = self.contact_link.replace(str(self.contact_id), str(uuid4()))
        missing_company = self.contact_link.replace(str(self.company_id), str(uuid4()))
        self.assertEqual(
            (await self.client.put(missing_contact, headers=self.headers)).status_code,
            404,
        )
        self.assertEqual(
            (await self.client.put(missing_company, headers=self.headers)).status_code,
            404,
        )
        original = SqlAlchemyCompanyLinkRepository.link

        async def fail(repository, link):
            await original(repository, link)
            raise RuntimeError("failure after insert")

        with patch.object(SqlAlchemyCompanyLinkRepository, "link", fail):
            response = await self.client.put(self.contact_link, headers=self.headers)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(await self.links(), [])

        async def fail_commit(uow):
            raise RuntimeError("commit failure")

        with patch.object(UnitOfWork, "commit", fail_commit):
            response = await self.client.put(self.contact_link, headers=self.headers)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(await self.links(), [])

        self.assertEqual(
            (
                await self.client.put(self.contact_link, headers=self.headers)
            ).status_code,
            204,
        )
        self.assertEqual(
            (
                await self.client.delete(self.company_item, headers=self.headers)
            ).status_code,
            204,
        )
        self.assertEqual(await self.links(), [])
