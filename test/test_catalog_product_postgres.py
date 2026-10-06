"""Catalog в двух схемах одноразовой PostgreSQL-базы."""

import os
import unittest
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.catalog.application.product.command.create_product.command import (
    CreateProductCommand,
    CreateProductContent,
)
from src.modules.catalog.application.product.command.create_product.handler import (
    CreateProductHandler,
)
from src.modules.catalog.application.product.command.put_product_content.command import (
    PutProductContentCommand,
)
from src.modules.catalog.application.product.command.put_product_content.handler import (
    PutProductContentHandler,
)
from src.modules.catalog.application.product.command.put_variant_content.command import (
    PutVariantContentCommand,
)
from src.modules.catalog.application.product.command.put_variant_content.handler import (
    PutVariantContentHandler,
)
from src.modules.catalog.application.product.query.get_product.handler import (
    GetProductHandler,
)
from src.modules.catalog.application.product.query.get_product.query import (
    GetProductQuery,
)
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.catalog.infrastructure.content_schema.persistence.repository import (
    SqlAlchemyContentSchemaRepository,
)
from src.modules.catalog.infrastructure.content_schema.rich_text_sanitizer import (
    Nh3RichTextSanitizer,
)
from src.modules.catalog.infrastructure.persistence.models.content_value import (
    ProductContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type import (
    ProductTypeContentBlockModel,
)
from src.modules.catalog.infrastructure.product.inventory_sku_reader import (
    InventorySkuReaderAdapter,
)
from src.modules.catalog.infrastructure.product.persistence.query_repository import (
    SqlAlchemyProductQueryRepository,
)
from src.modules.catalog.infrastructure.product.persistence.repository import (
    SqlAlchemyProductRepository,
)
from src.modules.catalog.infrastructure.reference_locale_reader import (
    ReferenceLocaleReaderAdapter,
)
from src.modules.inventory.infrastructure.persistence.models.sku import SkuModel
from src.modules.inventory.infrastructure.sku.persistence.query_repository import (
    SqlAlchemySkuQueryRepository,
)
from src.modules.reference_data.infrastructure.persistence.models.locale import (
    LocaleModel,
)
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
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

TEST_URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(TEST_URL, "Requires a disposable TEST_POSTGRES_URL")
class CatalogProductPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(TEST_URL, poolclass=NullPool)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant_ids = [uuid4(), uuid4()]
        self.schemas = [
            self.naming.schema_name(EntityIdVO(identifier))
            for identifier in self.tenant_ids
        ]
        self.actor = EntityIdVO(uuid4())
        self.sku_id = uuid4()
        self.now = datetime(2026, 10, 6, tzinfo=UTC)
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            for code in ("uk", "ru"):
                statement = pg_insert(LocaleModel).values(
                    code=code,
                    language_code=code,
                    script_code=None,
                    region_code=None,
                    country_code=None,
                    name=code,
                    active=True,
                )
                await connection.execute(
                    statement.on_conflict_do_update(
                        index_elements=[LocaleModel.code], set_={"active": True}
                    )
                )
            for schema in self.schemas:
                await connection.execute(CreateSchema(schema))
                await TenantMigrator().upgrade(connection, schema)
        async with self.tenant_uow(0) as uow:
            await uow.session.execute(
                insert(SkuModel).values(
                    id=self.sku_id,
                    code="SKU-1",
                    title="SKU",
                    created_by=self.actor.uuid,
                    updated_by=self.actor.uuid,
                )
            )

    async def asyncTearDown(self) -> None:
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )
        await self.engine.dispose()

    @asynccontextmanager
    async def tenant_uow(self, index: int):
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant_ids[index], self.naming)
            sessions = async_sessionmaker(connection, expire_on_commit=False)
            async with UnitOfWork(sessions) as uow:
                yield uow

    def handlers(self, session):
        products = SqlAlchemyProductRepository(session)
        skus = InventorySkuReaderAdapter(SqlAlchemySkuQueryRepository(session))
        locales = ReferenceLocaleReaderAdapter(SqlAlchemyCatalogRepository(session))
        schemas = SqlAlchemyContentSchemaRepository(session)
        clock = Mock(now=Mock(return_value=self.now))
        uuids = Mock(new=Mock(side_effect=(uuid4(), uuid4())))
        sanitizer = Nh3RichTextSanitizer()
        return (
            CreateProductHandler(
                products, skus, locales, clock, uuids, schemas, sanitizer
            ),
            GetProductHandler(SqlAlchemyProductQueryRepository(session), skus),
            PutProductContentHandler(products, locales, clock, schemas, sanitizer),
            schemas,
        )

    async def test_seed_uses_same_definition_in_both_scopes(self) -> None:
        for index in (0, 1):
            async with self.tenant_uow(index) as uow:
                schema = await SqlAlchemyContentSchemaRepository(
                    uow.session
                ).get_clean_type()
                self.assertEqual(schema.code, "clean")
                self.assertEqual(len(schema.blocks), 6)
                for code in ("title", "description", "short_description"):
                    self.assertEqual(
                        {
                            item.scope.value
                            for item in schema.blocks
                            if item.code == code
                        },
                        {"product", "variant"},
                    )
                self.assertEqual(sum(item.required for item in schema.blocks), 1)
                assignments = (
                    (await uow.session.execute(select(ProductTypeContentBlockModel)))
                    .scalars()
                    .all()
                )
                self.assertEqual(len(assignments), 6)

    async def test_values_audit_isolation_and_rollback(self) -> None:
        async with self.tenant_uow(0) as uow:
            create, _, _, _ = self.handlers(uow.session)
            result = await create.execute(
                CreateProductCommand(
                    self.actor,
                    self.sku_id,
                    (
                        CreateProductContent(
                            "uk", {"title": " Назва ", "description": "<p>Опис</p>"}
                        ),
                    ),
                )
            )
        async with self.tenant_uow(0) as uow:
            _, read, put, schemas = self.handlers(uow.session)
            details = await read.execute(
                GetProductQuery(ProductIdVO(result.id), ProductLocaleVO("uk"))
            )
            self.assertEqual(details.content.blocks["title"], "Назва")

            self.assertEqual(details.content.blocks["description"], "<p>Опис</p>")
            self.assertEqual(details.product_type_id, result.product_type_id)
            self.assertEqual(details.created_by, self.actor.uuid)
            await put.execute(
                PutProductContentCommand(
                    ProductIdVO(result.id), self.actor, "ru", 1, {"title": "Имя"}
                )
            )
            self.assertEqual(
                len(
                    (await uow.session.execute(select(ProductContentValueModel)))
                    .scalars()
                    .all()
                ),
                3,
            )
        async with self.tenant_uow(1) as uow:
            self.assertIsNone(
                await SqlAlchemyProductQueryRepository(uow.session).get_details(
                    ProductIdVO(result.id), ProductLocaleVO("uk")
                )
            )
        with self.assertRaises(RuntimeError):
            async with self.tenant_uow(0) as uow:
                _, _, put, _ = self.handlers(uow.session)
                await put.execute(
                    PutProductContentCommand(
                        ProductIdVO(result.id),
                        self.actor,
                        "uk",
                        1,
                        {"title": "Changed"},
                    )
                )
                raise RuntimeError("rollback")
        async with self.tenant_uow(0) as uow:
            details = await SqlAlchemyProductQueryRepository(uow.session).get_details(
                ProductIdVO(result.id), ProductLocaleVO("uk")
            )
            self.assertEqual(details.content.blocks["title"], "Назва")

    async def test_variant_content_is_independent_from_product_content(self) -> None:
        async with self.tenant_uow(0) as uow:
            create, _, _, _ = self.handlers(uow.session)
            created = await create.execute(
                CreateProductCommand(self.actor, self.sku_id, ())
            )
        async with self.tenant_uow(0) as uow:
            products = SqlAlchemyProductRepository(uow.session)
            schemas = SqlAlchemyContentSchemaRepository(uow.session)
            locales = ReferenceLocaleReaderAdapter(
                SqlAlchemyCatalogRepository(uow.session)
            )
            handler = PutVariantContentHandler(
                products,
                locales,
                Mock(now=Mock(return_value=self.now)),
                schemas,
                Nh3RichTextSanitizer(),
            )
            await handler.execute(
                PutVariantContentCommand(
                    ProductIdVO(created.id),
                    VariantIdVO(created.variant_id),
                    self.actor,
                    "uk",
                    1,
                    {"title": "Варіант"},
                )
            )
        async with self.tenant_uow(0) as uow:
            _, read, _, _ = self.handlers(uow.session)
            details = await read.execute(
                GetProductQuery(ProductIdVO(created.id), ProductLocaleVO("uk"))
            )
            self.assertIsNone(details.content)
            self.assertEqual(details.variants[0].content.blocks, {"title": "Варіант"})
