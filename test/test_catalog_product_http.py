"""HTTP-контракт динамического контента Catalog с auth и CSRF."""

import unittest
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.catalog.application.content_schema.contracts import (
    ProductTypeSchemaDTO,
    SchemaBlockDTO,
)
from src.modules.catalog.application.product.query.get_product.dto import (
    ProductCategoryDTO,
    ProductContentDTO,
    ProductDetailsDTO,
    ProductVariantDTO,
)
from src.modules.catalog.application.product.query.list_products.dto import (
    ProductListItemDTO,
)
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)
from src.modules.catalog.domain.product_type.aggregate import ContentScope
from src.modules.catalog.presentation.product.depends import (
    get_category_reader,
    get_content_schema_repository,
    get_locale_reader,
    get_product_query_repository,
    get_product_repository,
    get_sku_reader,
)
from src.modules.catalog.presentation.product.router import router
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.auth.depends import get_optional_request_context
from src.modules.identity.presentation.auth.http.csrf import issue_csrf
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.modules.shared.infrastructure.tokens.in_memory_token_backend import (
    InMemoryTokenBackend,
)
from src.modules.shared.presentation.tokens.depends import TokenManagerDep


class InMemoryProducts:
    def __init__(self, schema: ProductTypeSchemaDTO) -> None:
        self.rows = {}
        self.schema = schema

    async def add(self, product) -> None:
        self.rows[product.id.uuid] = product

    async def get_for_update(self, product_id):
        return self.rows.get(product_id.uuid)

    async def save_content(self, product, locale) -> None:
        self.rows[product.id.uuid] = product

    async def save_categories(self, product) -> None:
        self.rows[product.id.uuid] = product

    async def save_variants(self, product) -> None:
        self.rows[product.id.uuid] = product

    async def save_variant_content(self, product, variant_id, locale) -> None:
        self.rows[product.id.uuid] = product

    async def save_type(self, product) -> None:
        self.rows[product.id.uuid] = product

    async def delete(self, product) -> None:
        self.rows.pop(product.id.uuid)

    def codes(self, content, scope):
        if content is None:
            return None
        return ProductContentDTO(
            content.locale.value,
            {
                item.code: content.values[item.block_id]
                for item in self.schema.blocks
                if item.scope is scope and item.block_id in content.values
            },
        )

    async def list_products(self, locale):
        return tuple(
            ProductListItemDTO(
                product.id.uuid,
                product.kind,
                (
                    self.codes(
                        product.contents.get(locale.value), ContentScope.PRODUCT
                    ).blocks.get("title")
                    if locale.value in product.contents
                    else None
                ),
                len(product.variants),
                (
                    product.primary_category_id.uuid
                    if product.primary_category_id
                    else None
                ),
                None,
                product.updated_at,
            )
            for product in self.rows.values()
        )

    async def get_details(self, product_id, locale):
        product = self.rows.get(product_id.uuid)
        if product is None:
            return None
        return ProductDetailsDTO(
            id=product.id.uuid,
            kind=product.kind,
            product_type_id=product.product_type_id.uuid,
            schema_version=self.schema.schema_version,
            variant_id=product.variants[0].id.uuid,
            sku_id=product.variants[0].sku_id.uuid,
            sku_code=None,
            requested_locale=locale.value,
            content_locales=tuple(sorted(product.contents)),
            content=self.codes(
                product.contents.get(locale.value), ContentScope.PRODUCT
            ),
            categories=tuple(
                ProductCategoryDTO(item.uuid, None) for item in product.category_ids
            ),
            primary_category_id=(
                product.primary_category_id.uuid
                if product.primary_category_id
                else None
            ),
            created_at=product.created_at,
            updated_at=product.updated_at,
            created_by=product.created_by.uuid,
            updated_by=product.updated_by.uuid,
            variants=tuple(
                ProductVariantDTO(
                    item.id.uuid,
                    item.sku_id.uuid,
                    None,
                    tuple(item.contents),
                    self.codes(item.contents.get(locale.value), ContentScope.VARIANT),
                )
                for item in product.variants
            ),
        )


class ProductHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tenant, self.actor, self.sku = uuid4(), uuid4(), uuid4()
        self.product_id, self.variant_id = uuid4(), uuid4()
        self.title_id, self.description_id, self.type_id = uuid4(), uuid4(), uuid4()
        self.schema = ProductTypeSchemaDTO(
            self.type_id,
            "clean",
            True,
            1,
            {"uk": "Чистий"},
            (
                SchemaBlockDTO(
                    self.title_id,
                    "title",
                    ContentBlockType.TEXT,
                    ContentScope.PRODUCT,
                    True,
                    0,
                    {"uk": "Назва"},
                ),
                SchemaBlockDTO(
                    self.description_id,
                    "description",
                    ContentBlockType.RICH_TEXT,
                    ContentScope.PRODUCT,
                    False,
                    1,
                    {"uk": "Опис"},
                ),
                SchemaBlockDTO(
                    self.title_id,
                    "title",
                    ContentBlockType.TEXT,
                    ContentScope.VARIANT,
                    False,
                    0,
                    {"uk": "Назва"},
                ),
            ),
        )
        self.context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "session", ("member",)),
            None,
            None,
            None,
        )
        self.app = FastAPI()
        self.app.state.test_context = self.context
        self.app.state.token_manager = TokenManager(InMemoryTokenBackend())
        self.app.state.clock = Mock(
            now=Mock(return_value=datetime(2026, 10, 6, tzinfo=UTC))
        )
        self.app.state.uuid_generator = Mock(
            new=Mock(side_effect=(self.product_id, self.variant_id))
        )
        self.products = InMemoryProducts(self.schema)
        self.skus = Mock(
            get_code=AsyncMock(return_value="SKU-1"),
            get_codes=AsyncMock(
                side_effect=lambda ids: {item: "SKU-1" for item in ids}
            ),
        )
        self.locales = Mock(is_active=AsyncMock(return_value=True))
        self.schemas = Mock(
            get_clean_type=AsyncMock(return_value=self.schema),
            get_type=AsyncMock(return_value=self.schema),
        )
        self.app.dependency_overrides[get_optional_request_context] = (
            lambda: self.app.state.test_context
        )
        self.app.dependency_overrides[get_product_repository] = lambda: self.products
        self.app.dependency_overrides[get_product_query_repository] = (
            lambda: self.products
        )
        self.app.dependency_overrides[get_sku_reader] = lambda: self.skus
        self.app.dependency_overrides[get_locale_reader] = lambda: self.locales
        self.app.dependency_overrides[get_content_schema_repository] = (
            lambda: self.schemas
        )
        self.app.dependency_overrides[get_category_reader] = lambda: Mock(
            require_all=AsyncMock()
        )
        self.app.include_router(router, prefix="/api/console")

        @self.app.get("/csrf")
        async def csrf(request: Request, response: Response, tokens: TokenManagerDep):
            return await issue_csrf(request, response, tokens)

        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}
        self.collection = "/api/console/catalog/products"
        self.item = f"{self.collection}/{self.product_id}"

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_create_read_replace_and_delete_translation(self) -> None:
        created = await self.client.post(
            self.collection, json={"sku_id": str(self.sku)}, headers=self.headers
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["product_type_id"], str(self.type_id))
        empty = await self.client.get(self.item, params={"locale": "uk"})
        self.assertEqual(empty.status_code, 200, empty.text)
        self.assertIsNone(empty.json()["content"])
        payload = {
            "schema_version": 1,
            "blocks": {
                "title": " Назва ",
                "description": "<script>bad</script><p>Опис</p>",
            },
        }
        saved = await self.client.put(
            f"{self.item}/contents/uk", json=payload, headers=self.headers
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["blocks"]["title"], "Назва")
        self.assertNotIn("script", saved.json()["blocks"]["description"])
        read = await self.client.get(self.item, params={"locale": "uk"})
        self.assertEqual(read.json()["content"]["blocks"]["title"], "Назва")
        self.assertIsNone(read.json()["variants"][0]["content"])
        deleted = await self.client.delete(
            f"{self.item}/contents/uk", headers=self.headers
        )
        self.assertEqual(deleted.status_code, 204, deleted.text)
        self.assertIsNone(
            (await self.client.get(self.item, params={"locale": "uk"})).json()[
                "content"
            ]
        )

    async def test_create_with_explicit_product_type_uuid_string(self) -> None:
        invalid = await self.client.post(
            self.collection,
            json={"sku_id": str(self.sku), "product_type_id": "invalid-uuid"},
            headers=self.headers,
        )
        self.assertEqual(invalid.status_code, 422, invalid.text)
        self.assertEqual(invalid.json()["detail"][0]["loc"], ["body", "product_type_id"])
        self.assertFalse(self.products.rows)

        created = await self.client.post(
            self.collection,
            json={"sku_id": str(self.sku), "product_type_id": str(self.type_id)},
            headers=self.headers,
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["product_type_id"], str(self.type_id))
        self.schemas.get_type.assert_awaited_once_with(self.type_id, lock=True)

    async def test_auth_csrf_and_schema_validation(self) -> None:
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual(
            (await self.client.get(self.item, params={"locale": "uk"})).status_code, 401
        )
        self.app.state.test_context = self.context
        self.assertEqual(
            (
                await self.client.post(self.collection, json={"sku_id": str(self.sku)})
            ).status_code,
            403,
        )
        self.assertEqual(
            (
                await self.client.post(
                    self.collection,
                    json={"sku_id": str(self.sku), "tenant_id": str(self.tenant)},
                    headers=self.headers,
                )
            ).status_code,
            422,
        )
        self.assertEqual(
            (
                await self.client.post(
                    self.collection,
                    json={"sku_id": str(self.sku)},
                    headers=self.headers,
                )
            ).status_code,
            201,
        )
        invalid = await self.client.put(
            f"{self.item}/contents/uk",
            json={"schema_version": 1, "blocks": {}},
            headers=self.headers,
        )
        self.assertEqual(invalid.status_code, 422, invalid.text)
        stale = await self.client.put(
            f"{self.item}/contents/uk",
            json={"schema_version": 2, "blocks": {"title": "Name"}},
            headers=self.headers,
        )
        self.assertEqual(stale.status_code, 409, stale.text)
