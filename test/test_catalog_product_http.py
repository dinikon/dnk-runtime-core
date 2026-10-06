"""Контракт первых маршрутов Catalog с настоящими auth и CSRF dependencies."""

import unittest
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.catalog.application.product.query.get_product.dto import (
    ProductContentDTO,
    ProductDetailsDTO,
    ProductCategoryDTO,
    ProductVariantDTO,
)
from src.modules.catalog.application.product.query.list_products.dto import (
    ProductListItemDTO,
)
from src.modules.catalog.presentation.product.depends import (
    get_category_reader,
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
    def __init__(self) -> None:
        self.rows = {}

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

    async def delete(self, product) -> None:
        self.rows.pop(product.id.uuid)

    async def list_products(self, locale):
        return tuple(
            ProductListItemDTO(
                product.id.uuid,
                product.kind,
                (
                    product.contents.get(locale.value).name
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
        content = product.contents.get(locale.value)
        return ProductDetailsDTO(
            id=product.id.uuid,
            kind=product.kind,
            variant_id=product.variants[0].id.uuid,
            sku_id=product.variants[0].sku_id.uuid,
            sku_code=None,
            requested_locale=locale.value,
            content_locales=tuple(sorted(product.contents)),
            content=(
                ProductContentDTO(
                    locale=content.locale.value,
                    name=content.name,
                    description=content.description,
                )
                if content
                else None
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
                    item.contents.get(locale.value),
                )
                for item in product.variants
            ),
        )


class ProductHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tenant, self.actor, self.sku = uuid4(), uuid4(), uuid4()
        self.product_id, self.variant_id = uuid4(), uuid4()
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
            now=Mock(return_value=datetime(2026, 10, 5, tzinfo=UTC))
        )
        self.app.state.uuid_generator = Mock(
            new=Mock(side_effect=(self.product_id, self.variant_id))
        )
        self.products = InMemoryProducts()
        self.skus = Mock(
            get_code=AsyncMock(return_value="SKU-1"),
            get_codes=AsyncMock(
                side_effect=lambda ids: {item: "SKU-1" for item in ids}
            ),
        )
        self.locales = Mock(is_active=AsyncMock(return_value=True))
        self.categories = Mock(require_all=AsyncMock())
        self.app.dependency_overrides[get_optional_request_context] = (
            lambda: self.app.state.test_context
        )
        self.app.dependency_overrides[get_product_repository] = lambda: self.products
        self.app.dependency_overrides[get_product_query_repository] = (
            lambda: self.products
        )
        self.app.dependency_overrides[get_sku_reader] = lambda: self.skus
        self.app.dependency_overrides[get_locale_reader] = lambda: self.locales
        self.app.dependency_overrides[get_category_reader] = lambda: self.categories
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

    async def test_create_empty_read_null_and_put_translation(self) -> None:
        created = await self.client.post(
            self.collection, json={"sku_id": str(self.sku)}, headers=self.headers
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["kind"], "simple")
        self.assertNotIn("type", created.json())
        self.assertEqual(created.json()["content_locales"], [])
        self.assertEqual(created.json()["sku_code"], "SKU-1")
        missing = await self.client.get(self.item, params={"locale": "uk"})
        self.assertEqual(missing.status_code, 200, missing.text)
        self.assertEqual(missing.json()["kind"], "simple")
        self.assertIsNone(missing.json()["content"])
        self.assertEqual(
            set(missing.json()),
            {
                "id",
                "kind",
                "variant_id",
                "sku_id",
                "sku_code",
                "requested_locale",
                "content_locales",
                "content",
                "categories",
                "primary_category_id",
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
                "variants",
            },
        )
        self.assertEqual((await self.client.get(self.item)).status_code, 422)
        changed = await self.client.put(
            f"{self.item}/contents/sr-Latn",
            json={"name": " Ime ", "description": " Opis "},
            headers=self.headers,
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["name"], "Ime")
        read = await self.client.get(self.item, params={"locale": "sr-Latn"})
        self.assertEqual(read.json()["content"]["name"], "Ime")
        self.assertEqual(read.json()["content_locales"], ["sr-Latn"])
        self.assertEqual(set(read.json()["content"]), {"locale", "name", "description"})
        replaced = await self.client.put(
            f"{self.item}/contents/sr-Latn",
            json={"name": "Novo"},
            headers=self.headers,
        )
        self.assertEqual(replaced.status_code, 200, replaced.text)
        self.assertIsNone(replaced.json()["description"])
        self.assertIsNone(
            (await self.client.get(self.item, params={"locale": "uk"})).json()[
                "content"
            ]
        )

    async def test_auth_csrf_and_extra_fields(self) -> None:
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual(
            (await self.client.get(self.item, params={"locale": "uk"})).status_code,
            401,
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
        for removed_field in ("composition", "usage"):
            with self.subTest(field=removed_field):
                response = await self.client.post(
                    self.collection,
                    json={
                        "sku_id": str(self.sku),
                        "contents": [
                            {"locale": "uk", "name": "Name", removed_field: "Text"}
                        ],
                    },
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)
                response = await self.client.put(
                    f"{self.item}/contents/uk",
                    json={"name": "Name", removed_field: "Text"},
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 422)

    async def test_inactive_locale_and_missing_sku(self) -> None:
        self.skus.get_code.return_value = None
        self.assertEqual(
            (
                await self.client.post(
                    self.collection,
                    json={"sku_id": str(self.sku)},
                    headers=self.headers,
                )
            ).status_code,
            404,
        )
        self.skus.get_code.return_value = "SKU-1"
        self.locales.is_active.return_value = False
        self.assertEqual(
            (
                await self.client.post(
                    self.collection,
                    json={
                        "sku_id": str(self.sku),
                        "contents": [{"locale": "uk", "name": "Назва"}],
                    },
                    headers=self.headers,
                )
            ).status_code,
            422,
        )

    async def test_attribute_route_absent_and_variable_request_validated(self) -> None:
        self.assertEqual(
            (await self.client.get("/api/console/catalog/attributes")).status_code,
            404,
        )
        response = await self.client.post(
            f"{self.collection}/variable", json={}, headers=self.headers
        )
        self.assertEqual(response.status_code, 422)

    async def test_new_routes_require_authentication_and_csrf(self) -> None:
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual(
            (
                await self.client.get(self.collection, params={"locale": "uk"})
            ).status_code,
            401,
        )
        self.app.state.test_context = self.context
        self.assertEqual((await self.client.get(self.collection)).status_code, 422)
        self.assertEqual(
            (
                await self.client.post(
                    f"{self.collection}/variable",
                    json={"sku_ids": [str(uuid4()), str(uuid4())]},
                )
            ).status_code,
            403,
        )
        self.assertEqual((await self.client.delete(self.item)).status_code, 403)

    async def test_variable_variant_lifecycle_and_list(self) -> None:
        other_sku, third_sku = uuid4(), uuid4()
        self.app.state.uuid_generator.new.side_effect = (
            uuid4(),
            uuid4(),
            self.product_id,
            self.variant_id,
        )
        created = await self.client.post(
            f"{self.collection}/variable",
            json={"sku_ids": [str(self.sku), str(other_sku)]},
            headers=self.headers,
        )
        self.assertEqual(created.status_code, 201, created.text)
        product_id = created.json()["id"]
        item = f"{self.collection}/{product_id}"
        listed = await self.client.get(self.collection, params={"locale": "uk"})
        self.assertEqual(listed.json()[0]["variant_count"], 2)
        details = await self.client.get(item, params={"locale": "uk"})
        self.assertEqual(len(details.json()["variants"]), 2)
        self.assertEqual(details.json()["kind"], "variable")
        self.assertIsNone(details.json()["variant_id"])
        variant_id = details.json()["variants"][0]["id"]
        changed = await self.client.put(
            f"{item}/variants/{variant_id}/contents/uk",
            json={"short_description": " Первая позиция "},
            headers=self.headers,
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        read = await self.client.get(
            f"{item}/variants/{variant_id}", params={"locale": "uk"}
        )
        self.assertEqual(read.json()["short_description"], "Первая позиция")
        self.assertEqual(
            (
                await self.client.delete(
                    f"{item}/variants/{variant_id}", headers=self.headers
                )
            ).status_code,
            409,
        )
        self.app.state.uuid_generator.new.side_effect = (uuid4(),)
        added = await self.client.post(
            f"{item}/variants", json={"sku_id": str(third_sku)}, headers=self.headers
        )
        self.assertEqual(added.status_code, 201, added.text)
        self.assertEqual(
            (
                await self.client.delete(
                    f"{item}/variants/{variant_id}", headers=self.headers
                )
            ).status_code,
            204,
        )
        self.assertEqual(
            (await self.client.delete(item, headers=self.headers)).status_code, 204
        )
        self.assertEqual(
            (await self.client.get(self.collection, params={"locale": "uk"})).json(), []
        )

    async def test_simple_to_variable_structure_is_atomic(self) -> None:
        created = await self.client.post(
            self.collection, json={"sku_id": str(self.sku)}, headers=self.headers
        )
        self.assertEqual(created.status_code, 201, created.text)
        second_sku = uuid4()
        invalid = await self.client.put(
            f"{self.item}/variant-structure",
            json={
                "kind": "variable",
                "variants": [{"id": str(self.variant_id), "sku_id": str(self.sku)}],
            },
            headers=self.headers,
        )
        self.assertEqual(invalid.status_code, 409, invalid.text)
        self.assertEqual(
            (await self.client.get(self.item, params={"locale": "uk"})).json()["kind"],
            "simple",
        )
        self.app.state.uuid_generator.new.side_effect = (uuid4(),)
        changed = await self.client.put(
            f"{self.item}/variant-structure",
            json={
                "kind": "variable",
                "variants": [
                    {"id": str(self.variant_id), "sku_id": str(self.sku)},
                    {"sku_id": str(second_sku)},
                ],
            },
            headers=self.headers,
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(
            len(
                (await self.client.get(self.item, params={"locale": "uk"})).json()[
                    "variants"
                ]
            ),
            2,
        )
        restored = await self.client.put(
            f"{self.item}/variant-structure",
            json={
                "kind": "simple",
                "variants": [{"id": str(self.variant_id), "sku_id": str(self.sku)}],
            },
            headers=self.headers,
        )
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertEqual(
            (await self.client.get(self.item, params={"locale": "uk"})).json()["kind"],
            "simple",
        )

    async def test_replace_categories(self) -> None:
        category_id = uuid4()
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
        path = f"{self.item}/categories"
        self.assertEqual(
            (
                await self.client.put(
                    path,
                    json={
                        "category_ids": [str(category_id)],
                        "primary_category_id": str(category_id),
                    },
                    headers=self.headers,
                )
            ).status_code,
            200,
        )
        self.categories.require_all.assert_awaited_once_with((category_id,))
        read = await self.client.get(self.item, params={"locale": "uk"})
        self.assertEqual(
            read.json()["categories"], [{"id": str(category_id), "name": None}]
        )
        self.assertEqual(read.json()["primary_category_id"], str(category_id))
        self.assertEqual(
            (
                await self.client.put(
                    path,
                    json={
                        "category_ids": [str(category_id)],
                        "primary_category_id": None,
                    },
                    headers=self.headers,
                )
            ).status_code,
            422,
        )
        self.assertEqual(
            (
                await self.client.put(
                    path,
                    json={"category_ids": [], "primary_category_id": None},
                    headers=self.headers,
                )
            ).status_code,
            200,
        )
        self.assertEqual(
            (await self.client.get(self.item, params={"locale": "uk"})).json()[
                "categories"
            ],
            [],
        )
