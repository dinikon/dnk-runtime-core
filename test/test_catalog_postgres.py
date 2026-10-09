"""Реальный HTTP, табличное хранение и конкурирующие записи Catalog в PostgreSQL."""

import asyncio
import os
import unittest
from dataclasses import replace
from uuid import uuid4
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateSchema, DropSchema
from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence.global_migrations import (
    GlobalMigrator,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.catalog.presentation.router import router
from src.modules.catalog.infrastructure.product.persistence.repository import (
    SqlAlchemyProductRepository,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from test.crm_company_support import company_app

URL = os.environ.get("TEST_POSTGRES_URL")


@unittest.skipUnless(URL, "TEST_POSTGRES_URL requires a disposable database")
class CatalogPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет срез на свежих tenant-схемах с настоящими UoW и CSRF."""

    async def asyncSetUp(self) -> None:
        """Создаёт две независимые tenant-схемы и доверенную HTTP-сборку."""
        self.engine = create_async_engine(URL, poolclass=NullPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        self.tenant, self.other = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.actor = EntityIdVO(uuid4())
        self.schemas = [self.naming.schema_name(t) for t in (self.tenant, self.other)]
        async with self.engine.begin() as connection:
            await GlobalMigrator().upgrade(connection)
            self.locale_activity: dict[str, bool] = dict(
                (
                    await connection.execute(
                        text(
                            "SELECT code, active FROM public.ref_locales WHERE code IN ('ru', 'en')"
                        )
                    )
                ).all()
            )
            for code in ["ru", "en"]:
                await connection.execute(
                    text(
                        "INSERT INTO public.ref_locales(code,language_code,name,active) VALUES (:code,:code,:code,true) ON CONFLICT(code) DO UPDATE SET active=true"
                    ),
                    {"code": code},
                )
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
        self.app.include_router(router, prefix="/api/console")
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": token}
        self.base = "/api/console/catalog"

    async def asyncTearDown(self) -> None:
        """Удаляет тестовые схемы и восстанавливает активность справочника locale."""
        await self.client.aclose()
        async with self.engine.begin() as connection:
            for schema in self.schemas:
                await connection.execute(
                    DropSchema(schema, cascade=True, if_exists=True)
                )
            for code in ["ru", "en"]:
                if code in self.locale_activity:
                    await connection.execute(
                        text(
                            "UPDATE public.ref_locales SET active=:active WHERE code=:code"
                        ),
                        {"code": code, "active": self.locale_activity[code]},
                    )
                else:
                    await connection.execute(
                        text("DELETE FROM public.ref_locales WHERE code=:code"),
                        {"code": code},
                    )
        await self.engine.dispose()

    async def request(
        self, method: str, path: str, body: dict | None = None, status: int = 200
    ) -> dict:
        """Проверяет HTTP-статус и возвращает конкретный результат."""
        response = await self.client.request(
            method, self.base + path, headers=self.headers, json=body
        )
        self.assertEqual(response.status_code, status, response.text)
        return response.json() if status != 204 and status < 500 else {}

    async def create_product(self, **fields: object) -> dict:
        """Создаёт настоящий SIMPLE через HTTP."""
        return await self.request("POST", "/products/simple", fields, 201)

    async def test_translations_html_isolation_and_revisions(self) -> None:
        """Проверяет два scope, локали, sanitizer, принадлежность и tenant isolation."""
        types = await self.request("GET", "/product-types?locale=ru")
        default = types["items"][0]
        title = next(
            b["block_id"]
            for b in default["blocks"]
            if b["code"] == "title" and b["scope"] == "PRODUCT"
        )
        description = next(
            b["block_id"]
            for b in default["blocks"]
            if b["code"] == "description" and b["scope"] == "PRODUCT"
        )
        p = await self.create_product()
        item = "/products/" + p["id"]
        variant = item + "/variants/" + p["variant_id"]
        self.assertIsNone((await self.request("GET", item + "?locale=ru"))["content"])
        await self.request(
            "PUT",
            item + "/content/ru",
            {
                "expected_revision": 1,
                "expected_schema_version": 1,
                "values": {
                    title: "Термобутылка",
                    description: '<p onclick="bad()">Текст<script>alert(1)</script></p>',
                },
            },
        )
        saved = await self.request("GET", item + "?locale=ru")
        self.assertNotIn("script", saved["content"][description])
        self.assertNotIn("onclick", saved["content"][description])
        self.assertIsNone((await self.request("GET", item + "?locale=en"))["content"])
        await self.request(
            "PUT",
            variant + "/content/en",
            {
                "expected_revision": 2,
                "expected_schema_version": 1,
                "values": {title: "Position"},
            },
        )
        await self.request(
            "PUT",
            item + "/content/ru",
            {
                "expected_revision": 1,
                "expected_schema_version": 1,
                "values": {title: "stale"},
            },
            409,
        )
        await self.request(
            "GET", item + "/variants/" + str(uuid4()) + "?locale=ru", status=404
        )
        await self.request("GET", item, status=422)
        found = await self.request(
            "GET", "/products?locale=ru&search=Термобутылка&page_size=1"
        )
        self.assertEqual(found["total"], 1)
        async with self.engine.begin() as connection:
            await connection.execute(
                text("UPDATE public.ref_locales SET active=false WHERE code='ru'")
            )
        self.assertEqual(
            (await self.request("GET", item + "?locale=ru"))["content"][title],
            "Термобутылка",
        )
        await self.request(
            "PUT",
            item + "/content/ru",
            {
                "expected_revision": 3,
                "expected_schema_version": 1,
                "values": {title: "new"},
            },
            422,
        )
        self.app.state.test_context = replace(
            self.context,
            principal=replace(self.context.principal, tenant_id=str(self.other)),
        )
        await self.request("GET", item + "?locale=ru", status=404)
        self.assertEqual((await self.request("GET", "/products?locale=ru"))["total"], 0)

    async def test_custom_type_without_title_and_schema_protection(self) -> None:
        """Проверяет пользовательскую схему, ссылки, смену типа и удаление."""
        block = await self.request(
            "POST",
            "/content-blocks",
            {
                "code": "instructions",
                "locale": "en",
                "label": "Instructions",
                "value_type": "text",
            },
            201,
        )
        links = [
            {
                "block_id": block["id"],
                "scope": "PRODUCT",
                "required": True,
                "position": 0,
            }
        ]
        typ = await self.request(
            "POST",
            "/product-types",
            {
                "code": "equipment",
                "locale": "en",
                "label": "Equipment",
                "blocks": links,
            },
            201,
        )
        p = await self.create_product(product_type_id=typ["id"])
        item = "/products/" + p["id"]
        await self.request(
            "PUT",
            item + "/content/en",
            {
                "expected_revision": 1,
                "expected_schema_version": 1,
                "values": {block["id"]: "Manual"},
            },
        )
        await self.request(
            "PUT",
            "/product-types/" + typ["id"] + "/schema",
            {"expected_revision": 1, "expected_schema_version": 1, "blocks": []},
            422,
        )
        await self.request(
            "DELETE",
            "/content-blocks/" + block["id"] + "?expected_revision=1",
            status=409,
        )
        await self.request(
            "PUT",
            "/content-blocks/" + block["id"],
            {
                "expected_revision": 1,
                "locale": "en",
                "label": "Manual",
                "value_type": "rich_text",
            },
            409,
        )
        await self.request(
            "DELETE", "/product-types/" + typ["id"] + "?expected_revision=1", status=409
        )
        await self.request(
            "PUT",
            item + "/type",
            {
                "expected_revision": 2,
                "product_type_id": "c0000000-0000-4000-8000-000000000001",
            },
            422,
        )
        await self.request(
            "PUT",
            "/product-types/" + typ["id"] + "/translations/ru",
            {"expected_revision": 1, "label": "Оборудование"},
        )
        await self.request(
            "PUT",
            "/product-types/" + typ["id"] + "/schema",
            {
                "expected_revision": 2,
                "expected_schema_version": 1,
                "blocks": [{**links[0], "required": False}],
            },
        )
        await self.request(
            "PUT",
            item + "/content/en",
            {
                "expected_revision": 2,
                "expected_schema_version": 1,
                "values": {block["id"]: "stale schema"},
            },
            409,
        )
        await self.request(
            "DELETE", item + "/content/en?expected_revision=2", status=204
        )
        self.assertIsNone((await self.request("GET", item + "?locale=en"))["content"])
        await self.request(
            "PUT",
            item + "/variants/" + p["variant_id"] + "/properties",
            {"expected_revision": 3, "virtual": True, "downloadable": False},
        )
        await self.request(
            "PUT",
            item + "/variants/" + p["variant_id"] + "/properties",
            {"expected_revision": 4, "virtual": True, "downloadable": True},
            422,
        )
        await self.request("DELETE", item + "?expected_revision=4", status=204)
        await self.request(
            "DELETE", "/product-types/" + typ["id"] + "?expected_revision=3", status=204
        )
        await self.request(
            "DELETE",
            "/content-blocks/" + block["id"] + "?expected_revision=1",
            status=204,
        )

    async def test_system_definitions_duplicates_csrf_and_rollback(self) -> None:
        """Защищает системные данные и откатывает отказ после INSERT и commit."""
        await self.request(
            "DELETE",
            "/product-types/c0000000-0000-4000-8000-000000000001?expected_revision=1",
            status=409,
        )
        await self.request(
            "POST",
            "/content-blocks",
            {
                "code": "title",
                "locale": "en",
                "label": "Duplicate",
                "value_type": "text",
            },
            409,
        )
        response = await self.client.post(self.base + "/products/simple", json={})
        self.assertEqual(response.status_code, 403)
        original = SqlAlchemyProductRepository.add

        async def fail(
            repository: SqlAlchemyProductRepository, product: Product
        ) -> None:
            """Имитирует сбой после записи всех частей агрегата."""
            await original(repository, product)
            raise RuntimeError("write failed")

        with patch.object(SqlAlchemyProductRepository, "add", fail):
            await self.request("POST", "/products/simple", {}, 500)
        self.assertEqual((await self.request("GET", "/products?locale=en"))["total"], 0)

        async def commit_failure(uow: UnitOfWork) -> None:
            """Имитирует отказ commit внешнего UoW."""
            raise RuntimeError("commit failed")

        with patch.object(UnitOfWork, "commit", commit_failure):
            await self.request("POST", "/products/simple", {}, 500)
        self.assertEqual((await self.request("GET", "/products?locale=en"))["total"], 0)

    async def test_concurrent_schema_and_content_are_serialized(self) -> None:
        """Блокировка не оставляет контент, несовместимый с новой схемой."""
        block = await self.request(
            "POST",
            "/content-blocks",
            {"code": "note", "locale": "en", "label": "Note", "value_type": "text"},
            201,
        )
        links = [
            {
                "block_id": block["id"],
                "scope": "PRODUCT",
                "required": False,
                "position": 0,
            }
        ]
        typ = await self.request(
            "POST",
            "/product-types",
            {"code": "notes", "locale": "en", "label": "Notes", "blocks": links},
            201,
        )
        p = await self.create_product(product_type_id=typ["id"])
        content = self.client.put(
            self.base + "/products/" + p["id"] + "/content/en",
            headers=self.headers,
            json={
                "expected_revision": 1,
                "expected_schema_version": 1,
                "values": {block["id"]: "keep"},
            },
        )
        schema = self.client.put(
            self.base + "/product-types/" + typ["id"] + "/schema",
            headers=self.headers,
            json={"expected_revision": 1, "expected_schema_version": 1, "blocks": []},
        )
        a, b = await asyncio.gather(content, schema)
        self.assertIn((a.status_code, b.status_code), [(200, 422), (409, 200)])
        product = await self.request("GET", "/products/" + p["id"] + "?locale=en")
        current = await self.request(
            "GET", "/product-types/" + typ["id"] + "?locale=en"
        )
        if product["content"] is not None:
            self.assertEqual(len(current["blocks"]), 1)

    async def test_relational_constraints_empty_translation_and_migration(self) -> None:
        """Проверяет реальные FK, отсутствие JSON и round-trip пустого перевода."""
        from sqlalchemy.exc import IntegrityError

        p = await self.create_product()
        variant = "/products/" + p["id"] + "/variants/" + p["variant_id"]
        await self.request(
            "PUT",
            variant + "/content/en",
            {"expected_revision": 1, "expected_schema_version": 1, "values": {}},
        )
        self.assertEqual(
            (await self.request("GET", variant + "?locale=en"))["content"], {}
        )
        self.assertIsNone(
            (await self.request("GET", variant + "?locale=ru"))["content"]
        )
        async with self.engine.begin() as connection:
            types = (
                (
                    await connection.execute(
                        text(
                            "SELECT data_type FROM information_schema.columns WHERE table_schema=:schema AND table_name LIKE 'catalog_%'"
                        ),
                        {"schema": self.schemas[0]},
                    )
                )
                .scalars()
                .all()
            )
            self.assertTrue(types)
            self.assertTrue({"json", "jsonb"}.isdisjoint(types))
            rows = (
                (
                    await connection.execute(
                        text(
                            f'SELECT locale FROM "{self.schemas[0]}".catalog_variant_translations WHERE variant_id=:id'
                        ),
                        {"id": p["variant_id"]},
                    )
                )
                .scalars()
                .all()
            )
            self.assertEqual(rows, ["en"])
            with self.assertRaises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        text(
                            f"""INSERT INTO "{self.schemas[0]}".catalog_variant_content_values(variant_id,locale,block_id,value) VALUES (:id,'ru','c0000000-0000-4000-8000-000000000002','orphan')"""
                        ),
                        {"id": p["variant_id"]},
                    )

            await TenantMigrator().downgrade(
                connection, self.schemas[0], "0016_remove_inventory"
            )
            await TenantMigrator().upgrade(connection, self.schemas[0])
        self.assertEqual((await self.request("GET", "/products?locale=en"))["total"], 0)
        self.assertEqual(
            (await self.request("GET", "/product-types?locale=en"))["items"][0]["code"],
            "default",
        )


from src.modules.catalog.domain.product.aggregate import Product
