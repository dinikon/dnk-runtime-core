"""Реальный Catalog в двух tenant-схемах одноразовой PostgreSQL-базы."""

import os
import unittest
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
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
from src.modules.catalog.application.attribute.command.create_attribute.command import (
    CreateAttributeCommand,
    CreateAttributeContent,
    CreateAttributeOption,
)
from src.modules.catalog.application.attribute.command.create_attribute.handler import (
    CreateAttributeHandler,
)
from src.modules.catalog.application.product.command.create_variable_product.command import (
    CreateVariableProductCommand,
    CreateVariableProductContent,
    CreateVariableVariant,
    CreateVariantSelection,
)
from src.modules.catalog.application.product.command.create_variable_product.handler import (
    CreateVariableProductHandler,
)
from src.modules.catalog.application.product.command.put_product_content.command import (
    PutProductContentCommand,
)
from src.modules.catalog.application.product.command.put_product_content.handler import (
    PutProductContentHandler,
)
from src.modules.catalog.application.product.query.get_product.handler import (
    GetProductHandler,
)
from src.modules.catalog.application.product.query.get_product.query import (
    GetProductQuery,
)
from src.modules.catalog.domain.product.error import (
    ProductLocaleUnavailableError,
    ProductNotFoundError,
    ProductOptionUnavailableError,
    ProductSkuNotFoundError,
)
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.attribute.locale import AttributeLocaleVO
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO
from src.modules.catalog.infrastructure.persistence.models.product import ProductModel
from src.modules.catalog.infrastructure.persistence.models.variant import VariantModel
from src.modules.catalog.infrastructure.attribute.persistence.query_repository import (
    SqlAlchemyAttributeQueryRepository,
)
from src.modules.catalog.infrastructure.attribute.persistence.repository import (
    SqlAlchemyAttributeRepository,
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
from src.modules.catalog.presentation.product.router import router as product_router
from src.modules.catalog.presentation.attribute.router import router as attribute_router
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.auth.depends import get_optional_request_context
from src.modules.identity.presentation.auth.http.csrf import issue_csrf
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
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.infrastructure.tokens.in_memory_token_backend import (
    InMemoryTokenBackend,
)
from src.modules.shared.presentation.tokens.depends import TokenManagerDep
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
        self.now = datetime(2026, 10, 5, tzinfo=UTC)
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            for code, language in (("uk", "uk"), ("ru", "ru")):
                statement = pg_insert(LocaleModel).values(
                    code=code,
                    language_code=language,
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
        repository = SqlAlchemyProductRepository(session)
        skus = InventorySkuReaderAdapter(SqlAlchemySkuQueryRepository(session))
        locales = ReferenceLocaleReaderAdapter(SqlAlchemyCatalogRepository(session))
        clock = Mock(now=Mock(return_value=self.now))
        uuids = Mock(new=Mock(side_effect=(uuid4(), uuid4())))
        return (
            CreateProductHandler(repository, skus, locales, clock, uuids),
            GetProductHandler(SqlAlchemyProductQueryRepository(session), skus),
            PutProductContentHandler(repository, locales, clock),
        )

    async def test_create_reuse_translate_and_read_inactive_locale(self) -> None:
        async with self.tenant_uow(0) as uow:
            create, _, _ = self.handlers(uow.session)
            first = await create.execute(CreateProductCommand(self.actor, self.sku_id))
        async with self.tenant_uow(0) as uow:
            create, _, _ = self.handlers(uow.session)
            second = await create.execute(
                CreateProductCommand(
                    self.actor,
                    self.sku_id,
                    (CreateProductContent("uk", " Назва "),),
                )
            )
        self.assertNotEqual(first.id, second.id)
        async with self.tenant_uow(0) as uow:
            _, read, put = self.handlers(uow.session)
            empty = await read.execute(
                GetProductQuery(ProductIdVO(first.id), ProductLocaleVO("uk"))
            )
            self.assertIsNone(empty.content)
            changed = await put.execute(
                PutProductContentCommand(
                    ProductIdVO(first.id), self.actor, "ru", " Имя "
                )
            )
            self.assertEqual(changed.name, "Имя")
        async with self.engine.begin() as connection:
            await connection.execute(
                update(LocaleModel).where(LocaleModel.code == "ru").values(active=False)
            )
        async with self.tenant_uow(0) as uow:
            _, read, put = self.handlers(uow.session)
            details = await read.execute(
                GetProductQuery(ProductIdVO(first.id), ProductLocaleVO("ru"))
            )
            self.assertEqual(details.content.name, "Имя")
            self.assertEqual(details.sku_code, "SKU-1")
            with self.assertRaises(ProductLocaleUnavailableError):
                await put.execute(
                    PutProductContentCommand(
                        ProductIdVO(first.id), self.actor, "ru", "New"
                    )
                )

    async def test_tenant_isolation_and_rollback(self) -> None:
        async with self.tenant_uow(1) as uow:
            create, _, _ = self.handlers(uow.session)
            with self.assertRaises(ProductSkuNotFoundError):
                await create.execute(CreateProductCommand(self.actor, self.sku_id))
        product_id = uuid4()
        try:
            async with self.tenant_uow(0) as uow:
                create, _, _ = self.handlers(uow.session)
                result = await create.execute(
                    CreateProductCommand(self.actor, self.sku_id)
                )
                product_id = result.id
                raise RuntimeError("rollback after insert")
        except RuntimeError:
            pass
        async with self.tenant_uow(0) as uow:
            self.assertIsNone(
                await uow.session.scalar(
                    select(ProductModel.id).where(ProductModel.id == product_id)
                )
            )

    async def test_attribute_and_variable_product_persist_in_tenant(self) -> None:
        second_sku = uuid4()
        third_sku = uuid4()
        async with self.tenant_uow(0) as uow:
            await uow.session.execute(
                insert(SkuModel),
                [
                    dict(
                        id=identifier,
                        code=f"SKU-{index}",
                        title=f"SKU {index}",
                        created_by=self.actor.uuid,
                        updated_by=self.actor.uuid,
                    )
                    for index, identifier in enumerate((second_sku, third_sku), start=2)
                ],
            )
            locales = ReferenceLocaleReaderAdapter(
                SqlAlchemyCatalogRepository(uow.session)
            )
            attribute_handler = CreateAttributeHandler(
                SqlAlchemyAttributeRepository(uow.session),
                locales,
                Mock(now=Mock(return_value=self.now)),
                Mock(new=Mock(side_effect=uuid4)),
            )
            attribute = await attribute_handler.execute(
                CreateAttributeCommand(
                    actor_id=self.actor,
                    code="capsules",
                    options=tuple(
                        CreateAttributeOption(
                            code,
                            (CreateAttributeContent("uk", f"{code} капсул"),),
                        )
                        for code in ("100", "200", "500")
                    ),
                    contents=(CreateAttributeContent("uk", "Капсули"),),
                )
            )
            self.assertEqual(attribute.code, "capsules")
            reader = SqlAlchemyAttributeQueryRepository(uow.session)
            details = await reader.get_details(
                EntityIdVO(attribute.id), AttributeLocaleVO("uk")
            )
            self.assertEqual(details.name, "Капсули")
            self.assertEqual(len(details.options), 3)
            self.assertEqual(len(await reader.list_details(AttributeLocaleVO("uk"))), 1)
            sku_reader = InventorySkuReaderAdapter(
                SqlAlchemySkuQueryRepository(uow.session)
            )
            product_handler = CreateVariableProductHandler(
                SqlAlchemyProductRepository(uow.session),
                sku_reader,
                reader,
                locales,
                Mock(now=Mock(return_value=self.now)),
                Mock(new=Mock(side_effect=uuid4)),
            )
            created = await product_handler.execute(
                CreateVariableProductCommand(
                    actor_id=self.actor,
                    variants=tuple(
                        CreateVariableVariant(
                            sku_id=sku_id,
                            selections=(
                                CreateVariantSelection(attribute.id, option.id),
                            ),
                        )
                        for sku_id, option in zip(
                            (self.sku_id, second_sku, third_sku), attribute.options
                        )
                    ),
                    contents=(CreateVariableProductContent("uk", "Omega 3"),),
                )
            )
            self.assertEqual(len(created.variants), 3)
        async with self.tenant_uow(0) as uow:
            _, get, put = self.handlers(uow.session)
            details = await get.execute(
                GetProductQuery(ProductIdVO(created.id), ProductLocaleVO("uk"))
            )
            self.assertEqual(details.type, "VARIABLE")
            self.assertEqual(len(details.variants), 3)
            self.assertEqual(details.content.name, "Omega 3")
            self.assertEqual(
                details.variants[0].selections[0].attribute_name, "Капсули"
            )
            await put.execute(
                PutProductContentCommand(
                    ProductIdVO(created.id), self.actor, "ru", "Омега 3"
                )
            )
        rolled_back_id = None
        with self.assertRaises(RuntimeError):
            async with self.tenant_uow(0) as uow:
                reader = SqlAlchemyAttributeQueryRepository(uow.session)
                sku_reader = InventorySkuReaderAdapter(
                    SqlAlchemySkuQueryRepository(uow.session)
                )
                handler = CreateVariableProductHandler(
                    SqlAlchemyProductRepository(uow.session),
                    sku_reader,
                    reader,
                    ReferenceLocaleReaderAdapter(
                        SqlAlchemyCatalogRepository(uow.session)
                    ),
                    Mock(now=Mock(return_value=self.now)),
                    Mock(new=Mock(side_effect=uuid4)),
                )
                rolled_back_id = (
                    await handler.execute(
                        CreateVariableProductCommand(
                            actor_id=self.actor,
                            variants=(
                                CreateVariableVariant(
                                    self.sku_id,
                                    (
                                        CreateVariantSelection(
                                            attribute.id, attribute.options[0].id
                                        ),
                                    ),
                                ),
                                CreateVariableVariant(
                                    second_sku,
                                    (
                                        CreateVariantSelection(
                                            attribute.id, attribute.options[1].id
                                        ),
                                    ),
                                ),
                            ),
                        )
                    )
                ).id
                raise RuntimeError("rollback variable")
        async with self.tenant_uow(0) as uow:
            self.assertIsNone(await uow.session.get(ProductModel, rolled_back_id))
        async with self.tenant_uow(1) as uow:
            _, get, _ = self.handlers(uow.session)
            with self.assertRaises(ProductNotFoundError):
                await get.execute(
                    GetProductQuery(ProductIdVO(created.id), ProductLocaleVO("uk"))
                )
            reader = SqlAlchemyAttributeQueryRepository(uow.session)
            self.assertEqual(await reader.list_details(AttributeLocaleVO("uk")), ())
            isolated = CreateVariableProductHandler(
                SqlAlchemyProductRepository(uow.session),
                InventorySkuReaderAdapter(SqlAlchemySkuQueryRepository(uow.session)),
                reader,
                ReferenceLocaleReaderAdapter(SqlAlchemyCatalogRepository(uow.session)),
                Mock(now=Mock(return_value=self.now)),
                Mock(new=Mock(side_effect=uuid4)),
            )
            with self.assertRaises(ProductOptionUnavailableError):
                await isolated.execute(
                    CreateVariableProductCommand(
                        actor_id=self.actor,
                        variants=(
                            CreateVariableVariant(
                                self.sku_id,
                                (
                                    CreateVariantSelection(
                                        attribute.id, attribute.options[0].id
                                    ),
                                ),
                            ),
                            CreateVariableVariant(
                                self.sku_id,
                                (
                                    CreateVariantSelection(
                                        attribute.id, attribute.options[1].id
                                    ),
                                ),
                            ),
                        ),
                    )
                )
        async with self.tenant_uow(0) as uow:
            create, _, _ = self.handlers(uow.session)
            simple = (
                await create.execute(CreateProductCommand(self.actor, self.sku_id))
            ).id
        with self.assertRaises(IntegrityError):
            async with self.tenant_uow(0) as uow:
                await uow.session.execute(
                    insert(VariantModel).values(
                        id=uuid4(),
                        product_id=simple,
                        product_type="SIMPLE",
                        sku_id=self.sku_id,
                        combination_key="ANOTHER",
                    )
                )

    async def test_http_uses_bound_tenant_connection_and_commits_before_201(
        self,
    ) -> None:
        context = RequestContext(
            Principal(
                str(self.actor.uuid), str(self.tenant_ids[0]), "session", ("member",)
            ),
            None,
            None,
            None,
        )
        app = FastAPI()
        app.state.db = async_sessionmaker(self.engine, expire_on_commit=False)
        app.state.token_manager = TokenManager(InMemoryTokenBackend())
        app.state.test_context = context
        app.dependency_overrides[get_optional_request_context] = (
            lambda: app.state.test_context
        )
        app.include_router(product_router, prefix="/api/console")
        app.include_router(attribute_router, prefix="/api/console")

        engine = self.engine
        tenant_id = self.tenant_ids[0]
        naming = self.naming

        class BoundTenantConnection:
            def __init__(self, wrapped):
                self.wrapped = wrapped

            async def __call__(self, scope, receive, send):
                if scope["type"] != "http":
                    return await self.wrapped(scope, receive, send)
                async with engine.connect() as connection:
                    await bind_tenant_schema(connection, tenant_id, naming)
                    scope.setdefault("state", {})["tenant_connection"] = connection
                    await self.wrapped(scope, receive, send)

        app.add_middleware(BoundTenantConnection)

        @app.get("/csrf")
        async def csrf(request: Request, response: Response, tokens: TokenManagerDep):
            return await issue_csrf(request, response, tokens)

        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        collection = "/api/console/catalog/products"
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url=origin,
        ) as client:
            token = (await client.get("/csrf")).json()["csrf_token"]
            headers = {"Origin": origin, "X-CSRF-Token": token}
            created = await client.post(
                collection, json={"sku_id": str(self.sku_id)}, headers=headers
            )
            self.assertEqual(created.status_code, 201, created.text)
            product_id = created.json()["id"]
            read = await client.get(f"{collection}/{product_id}?locale=uk")
            self.assertEqual(read.status_code, 200, read.text)
            self.assertIsNone(read.json()["content"])
            translated = await client.put(
                f"{collection}/{product_id}/contents/uk",
                json={"name": " Назва "},
                headers=headers,
            )
            self.assertEqual(translated.status_code, 200, translated.text)
            self.assertEqual(
                (await client.get(f"{collection}/{product_id}?locale=uk")).json()[
                    "content"
                ]["name"],
                "Назва",
            )
            created_attribute = await client.post(
                "/api/console/catalog/attributes",
                json={
                    "code": "capsules",
                    "options": [{"code": code} for code in ("100", "200", "500")],
                },
                headers=headers,
            )
            self.assertEqual(created_attribute.status_code, 201, created_attribute.text)
            attribute = created_attribute.json()
            duplicate_attribute = await client.post(
                "/api/console/catalog/attributes",
                json={"code": "capsules", "options": [{"code": "10"}]},
                headers=headers,
            )
            self.assertEqual(duplicate_attribute.status_code, 409, duplicate_attribute.text)
            created_variable = await client.post(
                f"{collection}/variable",
                json={
                    "variants": [
                        {
                            "sku_id": str(self.sku_id),
                            "selections": [
                                {
                                    "attribute_id": attribute["id"],
                                    "option_id": option["id"],
                                }
                            ],
                        }
                        for option in attribute["options"]
                    ]
                },
                headers=headers,
            )
            self.assertEqual(created_variable.status_code, 201, created_variable.text)
            variable_id = created_variable.json()["id"]
            variable_read = await client.get(f"{collection}/{variable_id}?locale=uk")
            self.assertEqual(variable_read.status_code, 200, variable_read.text)
            self.assertEqual(variable_read.json()["type"], "VARIABLE")
            self.assertEqual(len(variable_read.json()["variants"]), 3)
        async with self.tenant_uow(0) as uow:
            self.assertIsNotNone(
                await uow.session.scalar(
                    select(ProductModel.id).where(ProductModel.id == product_id)
                )
            )
            self.assertIsNotNone(
                await uow.session.scalar(
                    select(ProductModel.id).where(ProductModel.id == variable_id)
                )
            )
