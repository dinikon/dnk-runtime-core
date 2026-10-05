"""Изоляция локалей tenant и транзакции на одноразовом PostgreSQL."""

from dataclasses import replace
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenancy.infrastructure.tenant_locale.persistence.model import (
    TenantLocaleModel,
)
from src.modules.tenancy.infrastructure.tenant_locale.persistence.repository import (
    SqlAlchemyTenantLocaleRepository,
)
from test.tenant_locale_support import tenant_locale_app

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL database."
)
class TenantLocalePostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant, self.other = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.actor = EntityIdVO(uuid4())
        self.schemas = [
            self.naming.schema_name(item) for item in (self.tenant, self.other)
        ]
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(CreateSchema(schema))
                await TenantMigrator().upgrade(connection, schema)
        self.context = RequestContext(
            Principal(str(self.actor.uuid), str(self.tenant.uuid), "test", ("member",)),
            None,
            None,
            None,
        )
        self.app = tenant_locale_app(
            self.sessions, self.context, scoped_connection=True
        )
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}
        self.path = "/api/console/tenants/locales"

    async def asyncTearDown(self):
        await self.client.aclose()
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )
        await self.engine.dispose()

    async def rows(self, schema):
        async with self.sessions() as session:
            result = await session.execute(
                select(TenantLocaleModel.__table__).execution_options(
                    schema_translate_map={"tenant": schema}
                )
            )
            return result.mappings().all()

    async def add(self, code):
        return await self.client.post(
            self.path, json={"code": code}, headers=self.headers
        )

    async def test_migration_and_tenant_isolation(self):
        async with self.engine.connect() as connection:
            for schema in self.schemas:
                tables = await connection.run_sync(
                    lambda conn: inspect(conn).get_table_names(schema=schema)
                )
                self.assertIn("tenant_locales", tables)
        self.assertEqual((await self.add("uk")).status_code, 201)
        self.assertEqual((await self.add("uk")).status_code, 409)
        self.assertEqual(
            [row["code"] for row in await self.rows(self.schemas[0])], ["uk"]
        )
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other.uuid)),
        )
        self.assertEqual((await self.client.get(self.path)).json(), [])
        self.assertEqual((await self.add("uk")).status_code, 201)
        self.assertEqual(
            [row["code"] for row in await self.rows(self.schemas[1])], ["uk"]
        )
        self.assertEqual(
            (
                await self.client.delete(f"{self.path}/uk", headers=self.headers)
            ).status_code,
            204,
        )
        self.assertEqual(await self.rows(self.schemas[1]), [])
        self.assertEqual(len(await self.rows(self.schemas[0])), 1)

    async def test_failure_after_insert_rolls_back(self):
        original = SqlAlchemyTenantLocaleRepository.add

        async def fail(repository, locale):
            await original(repository, locale)
            raise RuntimeError("after insert")

        with patch.object(SqlAlchemyTenantLocaleRepository, "add", fail):
            response = await self.add("en")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(await self.rows(self.schemas[0]), [])
        self.assertEqual((await self.add("en")).status_code, 201)
