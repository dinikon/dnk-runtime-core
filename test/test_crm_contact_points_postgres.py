"""CRM и ContactPoints работают в одной tenant-транзакции PostgreSQL."""

from dataclasses import replace
import os
import unittest
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.contact_points.infrastructure.persistence.models.contact_point import (
    ContactPointModel,
)
from src.modules.contact_points.infrastructure.persistence.models.contact_point_binding import (
    ContactPointBindingModel,
)
from src.modules.crm.presentation.company.router import router as company_router
from src.modules.identity.domain.auth.principal import Principal
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from test.crm_contact_support import contact_app

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL database."
)
class CrmContactPointsPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant, self.other = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.schemas = [self.naming.schema_name(t) for t in (self.tenant, self.other)]
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(CreateSchema(schema))
                await TenantMigrator().upgrade(connection, schema)
        actor = uuid4()
        from src.modules.identity.domain.auth.request_context import RequestContext

        context = RequestContext(
            Principal(str(actor), str(self.tenant.uuid), "test", ("member",)),
            None,
            None,
            None,
        )
        self.app = contact_app(self.sessions, context, scoped_connection=True)
        self.app.include_router(company_router, prefix="/api/console")
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

    async def count(self, model):
        async with self.sessions() as session:
            return await session.scalar(
                select(func.count())
                .select_from(model.__table__)
                .execution_options(schema_translate_map={"tenant": self.schemas[0]})
            )

    async def test_shared_value_isolated_targets_and_atomic_cleanup(self):
        contact = await self.client.post(
            "/api/console/crm/contacts",
            headers=self.headers,
            json={"first_name": "Jane"},
        )
        company = await self.client.post(
            "/api/console/crm/companies",
            headers=self.headers,
            json={"legal_name": "Acme"},
        )
        self.assertEqual(contact.status_code, 201, contact.text)
        self.assertEqual(company.status_code, 201, company.text)
        contact_url = f"/api/console/crm/contacts/{contact.json()['id']}/contact-points"
        company_url = (
            f"/api/console/crm/companies/{company.json()['id']}/contact-points"
        )
        first = await self.client.put(
            contact_url,
            headers=self.headers,
            json={
                "phones": [{"value": "050 123 45 67", "country_code": "UA"}],
                "emails": [{"value": "Name@Example.COM"}],
            },
        )
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["phones"][0]["value"], "+380501234567")
        self.assertEqual(first.json()["emails"][0]["value"], "Name@example.com")
        self.assertEqual(
            (await self.client.get(company_url)).json(), {"phones": [], "emails": []}
        )
        second = await self.client.put(
            company_url,
            headers=self.headers,
            json={"phones": [], "emails": [{"value": "Name@Example.COM"}]},
        )
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(
            second.json()["emails"][0]["contact_point_id"],
            first.json()["emails"][0]["contact_point_id"],
        )
        self.assertNotEqual(
            second.json()["emails"][0]["binding_id"],
            first.json()["emails"][0]["binding_id"],
        )
        self.assertEqual(await self.count(ContactPointModel), 2)
        self.assertEqual(await self.count(ContactPointBindingModel), 3)
        invalid = await self.client.patch(
            company_url,
            headers=self.headers,
            json={"phones": [{"value": "123", "country_code": "UA"}]},
        )
        self.assertEqual(invalid.status_code, 422, invalid.text)
        self.assertEqual((await self.client.get(company_url)).json(), second.json())
        self.app.state.test_context = replace(
            self.app.state.test_context,
            principal=replace(
                self.app.state.test_context.principal, tenant_id=str(self.other.uuid)
            ),
        )
        self.assertEqual((await self.client.get(contact_url)).status_code, 404)
        self.app.state.test_context = replace(
            self.app.state.test_context,
            principal=replace(
                self.app.state.test_context.principal, tenant_id=str(self.tenant.uuid)
            ),
        )
        deleted = await self.client.delete(
            f"/api/console/crm/contacts/{contact.json()['id']}",
            headers=self.headers,
        )
        self.assertEqual(deleted.status_code, 204, deleted.text)
        self.assertEqual(await self.count(ContactPointBindingModel), 1)
        self.assertEqual(await self.count(ContactPointModel), 2)
        self.assertEqual((await self.client.get(company_url)).json(), second.json())
        deleted_company = await self.client.delete(
            f"/api/console/crm/companies/{company.json()['id']}",
            headers=self.headers,
        )
        self.assertEqual(deleted_company.status_code, 204, deleted_company.text)
        self.assertEqual(await self.count(ContactPointBindingModel), 0)
        self.assertEqual(await self.count(ContactPointModel), 2)
