"""Реальная tenant-схема, дерево Category и связи Product."""

import asyncio
import os
import unittest
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema

from src.config import dnk_config
from src.modules.catalog.application.category.command.create_category.command import (
    CreateCategoryCommand,
    CreateCategoryTranslation,
)
from src.modules.catalog.application.category.command.create_category.handler import (
    CreateCategoryHandler,
)
from src.modules.catalog.application.category.command.delete_category.command import (
    DeleteCategoryCommand,
)
from src.modules.catalog.application.category.command.delete_category.handler import (
    DeleteCategoryHandler,
)
from src.modules.catalog.application.category.command.move_category.command import (
    MoveCategoryCommand,
)
from src.modules.catalog.application.category.command.move_category.handler import (
    MoveCategoryHandler,
)
from src.modules.catalog.application.category.command.put_category_content.command import (
    PutCategoryContentCommand,
)
from src.modules.catalog.application.category.command.put_category_content.handler import (
    PutCategoryContentHandler,
)
from src.modules.catalog.application.category.query.get_category.handler import (
    GetCategoryHandler,
)
from src.modules.catalog.application.category.query.get_category.query import (
    GetCategoryQuery,
)
from src.modules.catalog.application.category.query.list_categories.handler import (
    ListCategoriesHandler,
)
from src.modules.catalog.application.category.query.list_categories.query import (
    ListCategoriesQuery,
)
from src.modules.catalog.application.product.command.put_product_categories.command import (
    PutProductCategoriesCommand,
)
from src.modules.catalog.application.product.command.put_product_categories.handler import (
    PutProductCategoriesHandler,
)
from src.modules.catalog.infrastructure.content_schema.persistence.repository import (
    SqlAlchemyContentSchemaRepository,
)
from src.modules.catalog.domain.category.error import (
    CategoryCycleError,
    CategoryInUseError,
    CategoryLocaleUnavailableError,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.category.value_object.locale import CategoryLocaleVO
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.catalog.infrastructure.category.persistence.query_repository import (
    SqlAlchemyCategoryQueryRepository,
)
from src.modules.catalog.infrastructure.category.persistence.repository import (
    SqlAlchemyCategoryRepository,
)
from src.modules.catalog.infrastructure.persistence.models.category import CategoryModel
from src.modules.catalog.infrastructure.persistence.models.product import ProductModel
from src.modules.catalog.infrastructure.persistence.models.product_category import (
    ProductCategoryModel,
)
from src.modules.catalog.infrastructure.persistence.models.variant import VariantModel
from src.modules.catalog.infrastructure.product.category_reader import (
    SqlAlchemyCategoryReader,
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


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Requires a disposable TEST_POSTGRES_URL"
)
class CatalogCategoryPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            os.environ["TEST_POSTGRES_URL"], poolclass=NullPool
        )
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenants = (uuid4(), uuid4())
        self.schemas = tuple(
            self.naming.schema_name(EntityIdVO(item)) for item in self.tenants
        )
        self.actor = EntityIdVO(uuid4())
        self.now = datetime(2026, 10, 5, tzinfo=UTC)
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

    async def asyncTearDown(self) -> None:
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )
        await self.engine.dispose()

    @asynccontextmanager
    async def uow(self, tenant_index=0):
        async with self.engine.connect() as connection:
            await bind_tenant_schema(
                connection, self.tenants[tenant_index], self.naming
            )
            async with UnitOfWork(
                async_sessionmaker(connection, expire_on_commit=False)
            ) as uow:
                yield uow

    def handlers(self, session, tenant_index=0):
        repo = SqlAlchemyCategoryRepository(session)
        query = SqlAlchemyCategoryQueryRepository(session)
        locales = ReferenceLocaleReaderAdapter(SqlAlchemyCatalogRepository(session))
        clock = Mock(now=Mock(return_value=self.now))
        return (
            CreateCategoryHandler(
                repo, locales, clock, Mock(new=Mock(side_effect=uuid4))
            ),
            MoveCategoryHandler(repo, clock),
            DeleteCategoryHandler(repo),
            GetCategoryHandler(query),
            ListCategoriesHandler(query),
        )

    async def create(self, tenant_index=0, parent_id=None, name="Назва"):
        async with self.uow(tenant_index) as uow:
            handler = self.handlers(uow.session)[0]
            return await handler.execute(
                CreateCategoryCommand(
                    EntityIdVO(self.tenants[tenant_index]),
                    self.actor,
                    parent_id,
                    (CreateCategoryTranslation("uk", name),),
                )
            )

    async def test_tree_projection_locale_and_isolation(self) -> None:
        root = await self.create()
        child = await self.create(parent_id=root.id, name="Дитина")
        async with self.uow() as uow:
            _, _, _, get, listing = self.handlers(uow.session)
            items = await listing.execute(ListCategoriesQuery(CategoryLocaleVO("uk")))
            self.assertEqual({item.id for item in items}, {root.id, child.id})
            self.assertEqual(
                next(item.parent_id for item in items if item.id == child.id), root.id
            )
            detail = await get.execute(
                GetCategoryQuery(CategoryIdVO(root.id), CategoryLocaleVO("ru"))
            )
            self.assertIsNone(detail.name)
            self.assertEqual(detail.translations[0].name, "Назва")
            writer = PutCategoryContentHandler(
                SqlAlchemyCategoryRepository(uow.session),
                ReferenceLocaleReaderAdapter(SqlAlchemyCatalogRepository(uow.session)),
                Mock(now=Mock(return_value=self.now)),
            )
            await writer.execute(
                PutCategoryContentCommand(
                    CategoryIdVO(root.id), self.actor, "ru", " Имя "
                )
            )
            await writer.execute(
                PutCategoryContentCommand(
                    CategoryIdVO(root.id), self.actor, "ru", " Новое имя "
                )
            )
            updated = await get.execute(
                GetCategoryQuery(CategoryIdVO(root.id), CategoryLocaleVO("ru"))
            )
            self.assertEqual(updated.name, "Новое имя")
        async with self.uow(1) as uow:
            self.assertEqual(
                await self.handlers(uow.session)[4].execute(
                    ListCategoriesQuery(CategoryLocaleVO("uk"))
                ),
                (),
            )
        async with self.engine.begin() as connection:
            await connection.execute(
                update(LocaleModel).where(LocaleModel.code == "uk").values(active=False)
            )
        async with self.uow() as uow:
            detail = await self.handlers(uow.session)[3].execute(
                GetCategoryQuery(CategoryIdVO(root.id), CategoryLocaleVO("uk"))
            )
            self.assertEqual(detail.name, "Назва")
            writer = PutCategoryContentHandler(
                SqlAlchemyCategoryRepository(uow.session),
                ReferenceLocaleReaderAdapter(SqlAlchemyCatalogRepository(uow.session)),
                Mock(now=Mock(return_value=self.now)),
            )
            with self.assertRaises(CategoryLocaleUnavailableError):
                await writer.execute(
                    PutCategoryContentCommand(
                        CategoryIdVO(root.id), self.actor, "uk", "Новое"
                    )
                )

    async def test_cycle_delete_constraints_and_product_assignment(self) -> None:
        root = await self.create()
        child = await self.create(parent_id=root.id)
        async with self.uow() as uow:
            _, move, delete, _, _ = self.handlers(uow.session)
            with self.assertRaises(CategoryCycleError):
                await move.execute(
                    MoveCategoryCommand(
                        EntityIdVO(self.tenants[0]),
                        CategoryIdVO(root.id),
                        CategoryIdVO(child.id),
                        self.actor,
                    )
                )
            with self.assertRaises(CategoryInUseError):
                await delete.execute(
                    DeleteCategoryCommand(
                        EntityIdVO(self.tenants[0]), CategoryIdVO(root.id)
                    )
                )
        product_id = uuid4()
        async with self.uow() as uow:
            clean_type = await SqlAlchemyContentSchemaRepository(
                uow.session
            ).get_clean_type()
            await uow.session.execute(
                insert(ProductModel).values(
                    id=product_id,
                    kind="simple",
                    product_type_id=clean_type.id,
                    created_by=self.actor.uuid,
                    updated_by=self.actor.uuid,
                )
            )
            await uow.session.execute(
                insert(VariantModel).values(
                    id=uuid4(), product_id=product_id, sku_id=uuid4()
                )
            )
            handler = PutProductCategoriesHandler(
                SqlAlchemyProductRepository(uow.session),
                SqlAlchemyCategoryReader(uow.session),
                Mock(now=Mock(return_value=self.now)),
            )
            result = await handler.execute(
                PutProductCategoriesCommand(
                    ProductIdVO(product_id), self.actor, (root.id, child.id), root.id
                )
            )
            self.assertEqual(result.primary_category_id, root.id)
        async with self.uow() as uow:
            rows = (
                (
                    await uow.session.execute(
                        select(ProductCategoryModel).where(
                            ProductCategoryModel.product_id == product_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            self.assertEqual(sum(item.is_primary for item in rows), 1)
            projection = await SqlAlchemyProductQueryRepository(
                uow.session
            ).get_details(ProductIdVO(product_id), ProductLocaleVO("uk"))
            self.assertEqual(
                {item.id for item in projection.categories}, {root.id, child.id}
            )
            with self.assertRaises(CategoryInUseError):
                await self.handlers(uow.session)[2].execute(
                    DeleteCategoryCommand(
                        EntityIdVO(self.tenants[0]), CategoryIdVO(child.id)
                    )
                )
        other = await self.create()
        with self.assertRaises(IntegrityError):
            async with self.uow() as uow:
                await uow.session.execute(
                    insert(ProductCategoryModel).values(
                        product_id=product_id, category_id=other.id, is_primary=True
                    )
                )

    async def test_concurrent_reverse_moves_do_not_cycle(self) -> None:
        first, second = await self.create(), await self.create()

        async def move(category, parent):
            try:
                async with self.uow() as uow:
                    return await self.handlers(uow.session)[1].execute(
                        MoveCategoryCommand(
                            EntityIdVO(self.tenants[0]),
                            CategoryIdVO(category),
                            CategoryIdVO(parent),
                            self.actor,
                        )
                    )
            except CategoryCycleError:
                return None

        results = await asyncio.gather(
            move(first.id, second.id), move(second.id, first.id)
        )
        self.assertEqual(sum(item is None for item in results), 1)

    async def test_rollback(self) -> None:
        category_id = None
        try:
            async with self.uow() as uow:
                result = await self.handlers(uow.session)[0].execute(
                    CreateCategoryCommand(
                        EntityIdVO(self.tenants[0]),
                        self.actor,
                        None,
                        (CreateCategoryTranslation("uk", "Temporary"),),
                    )
                )
                category_id = result.id
                raise RuntimeError("rollback")
        except RuntimeError:
            pass
        async with self.uow() as uow:
            self.assertIsNone(
                await uow.session.scalar(
                    select(CategoryModel.id).where(CategoryModel.id == category_id)
                )
            )

    async def test_delete_unlinked_tree(self) -> None:
        root = await self.create()
        child = await self.create(parent_id=root.id)
        async with self.uow() as uow:
            delete = self.handlers(uow.session)[2]
            await delete.execute(
                DeleteCategoryCommand(
                    EntityIdVO(self.tenants[0]), CategoryIdVO(child.id)
                )
            )
            await delete.execute(
                DeleteCategoryCommand(
                    EntityIdVO(self.tenants[0]), CategoryIdVO(root.id)
                )
            )
        async with self.uow() as uow:
            self.assertIsNone(
                await uow.session.scalar(
                    select(CategoryModel.id).where(CategoryModel.id == root.id)
                )
            )
