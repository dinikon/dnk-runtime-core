"""SKU, изоляция, конкурентная уникальность и миграция на одноразовом PostgreSQL."""

import asyncio
from dataclasses import replace
import os
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.inventory.infrastructure.persistence.models.sku import SkuModel
from src.modules.inventory.infrastructure.sku.persistence.repository import (
    SqlAlchemySkuRepository,
)
from src.modules.inventory.infrastructure.sku.persistence.query_repository import (
    SqlAlchemySkuQueryRepository,
)
from src.modules.inventory.domain.sku.value_object.identifier import SkuIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from test.inventory_sku_support import sku_app

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(
    TEST_URL, "Set TEST_POSTGRES_URL to a disposable PostgreSQL database."
)
class SkuPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant, self.other = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.actor = EntityIdVO(uuid4())
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
        self.app = sku_app(self.sessions, self.context, scoped_connection=True)
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}
        self.collection = "/api/console/inventory/skus"

    async def asyncTearDown(self):
        await self.client.aclose()
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )
        await self.engine.dispose()

    async def create(self, code=" OMEGA-100 ", title=" Omega 100 "):
        return await self.client.post(
            self.collection, headers=self.headers, json=dict(code=code, title=title)
        )

    async def rows(self):
        async with self.sessions() as session:
            result = await session.execute(
                select(SkuModel.__table__).execution_options(
                    schema_translate_map={"tenant": self.schemas[0]}
                )
            )
            return result.mappings().all()

    async def test_create_read_tenant_isolation_and_case_sensitive_codes(self):
        response = await self.create()
        self.assertEqual(response.status_code, 201, response.text)
        record = response.json()
        identifier = record["id"]
        self.assertEqual(record["code"], "OMEGA-100")
        self.assertEqual(record["created_by"], str(self.actor))
        self.assertEqual(
            (await self.client.get(f"{self.collection}/{identifier}")).json(), record
        )
        self.assertEqual((await self.create()).status_code, 409)
        self.assertEqual((await self.create("omega-100")).status_code, 201)
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        self.assertEqual((await self.client.get(self.collection)).json(), [])
        self.assertEqual(
            (await self.client.get(f"{self.collection}/{identifier}")).status_code, 404
        )
        self.assertEqual((await self.create()).status_code, 201)
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.other.uuid, self.naming)
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                self.assertIsNone(
                    await SqlAlchemySkuQueryRepository(uow.session).get_details(
                        sku_id=SkuIdVO(UUID(identifier))
                    )
                )
        self.assertEqual(len(await self.rows()), 2)

    async def test_concurrent_duplicate_code_creates_only_one_sku(self):
        responses = await asyncio.gather(self.create("SAME"), self.create(" SAME "))
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [201, 409],
            [r.text for r in responses],
        )
        self.assertEqual(len(await self.rows()), 1)
        self.assertEqual((await self.client.get(self.collection)).status_code, 200)

    async def test_list_is_bounded_and_sorted_across_pages(self):
        for code in ("C", "A", "B"):
            self.assertEqual((await self.create(code)).status_code, 201)
        first = await self.client.get(self.collection, params=dict(limit=2, offset=0))
        second = await self.client.get(self.collection, params=dict(limit=2, offset=2))
        self.assertEqual([r["code"] for r in first.json()], ["A", "B"])
        self.assertEqual([r["code"] for r in second.json()], ["C"])
        self.assertEqual(
            (await self.client.get(self.collection, params=dict(offset=3))).json(), []
        )

    async def test_failure_after_insert_rolls_back_without_losing_next_request(self):
        original = SqlAlchemySkuRepository.add

        async def fail(repository, sku):
            await original(repository, sku)
            raise RuntimeError("after insert")

        with patch.object(SqlAlchemySkuRepository, "add", fail):
            response = await self.create()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(await self.rows(), [])
        self.assertEqual((await self.create()).status_code, 201)

    async def test_query_repository_reads_only_bound_tenant(self):
        response = await self.create()

        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                repository = SqlAlchemySkuQueryRepository(uow.session)
                details = await repository.get_details(
                    sku_id=SkuIdVO(UUID(response.json()["id"]))
                )
                self.assertIsNotNone(details)
                self.assertEqual(details.code, "OMEGA-100")
                self.assertIsNone(await repository.get_details(sku_id=SkuIdVO(uuid4())))

    async def test_migration_downgrade_upgrade_is_scoped_and_preserves_warehouse(self):
        migrator = TenantMigrator()
        schema = self.schemas[0]
        warehouse = uuid4()
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    f'INSERT INTO "{schema}".warehouses (id,title,created_by,updated_by) VALUES (:id,:title,:actor,:actor)'
                ),
                dict(id=warehouse, title="Main", actor=self.actor.uuid),
            )
            await migrator.downgrade(connection, schema, "0010_crm_company_legal_name")
            self.assertNotIn(
                "skus",
                await connection.run_sync(
                    lambda c: inspect(c).get_table_names(schema=schema)
                ),
            )
            self.assertIn(
                "skus",
                await connection.run_sync(
                    lambda c: inspect(c).get_table_names(schema=self.schemas[1])
                ),
            )
            await migrator.upgrade(connection, schema)
            self.assertEqual(
                await connection.scalar(text(f'SELECT id FROM "{schema}".warehouses')),
                warehouse,
            )
            self.assertEqual(
                await migrator.current(connection, schema), (migrator.head(),)
            )
