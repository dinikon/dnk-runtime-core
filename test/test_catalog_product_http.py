"""Контракт первых маршрутов Catalog с настоящими auth и CSRF dependencies."""

import unittest
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.catalog.application.product.query.get_product.dto import (
    ProductContentDTO,
    ProductDetailsDTO,
    ProductSelectionDTO,
    ProductVariantDTO,
    VariableProductDetailsDTO,
)
from src.modules.catalog.application.attribute.query.list_attributes.dto import (
    AttributeDetailsDTO,
    AttributeOptionDTO,
)
from src.modules.catalog.domain.attribute.error import AttributeAlreadyExistsError
from src.modules.catalog.presentation.attribute.depends import (
    get_attribute_locale_reader,
    get_attribute_query_repository,
    get_attribute_repository,
)
from src.modules.catalog.presentation.attribute.router import router as attribute_router
from src.modules.catalog.presentation.product.depends import (
    get_attribute_reader,
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

    async def get_details(self, product_id, locale):
        product = self.rows.get(product_id.uuid)
        if product is None:
            return None
        content = product.contents.get(locale.value)
        if product.type == "VARIABLE":
            return VariableProductDetailsDTO(
                id=product.id.uuid,
                type=product.type,
                variants=tuple(
                    ProductVariantDTO(
                        id=variant.id.uuid,
                        sku_id=variant.sku_id.uuid,
                        sku_code=None,
                        selections=tuple(
                            ProductSelectionDTO(
                                attribute_id=item.attribute_id.uuid,
                                attribute_code="capsules",
                                attribute_name=(
                                    "Капсули" if locale.value == "uk" else None
                                ),
                                option_id=item.option_id.uuid,
                                option_code=self.option_codes[item.option_id.uuid],
                                option_name=None,
                            )
                            for item in variant.selections
                        ),
                    )
                    for variant in product.variants
                ),
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
                created_at=product.created_at,
                updated_at=product.updated_at,
                created_by=product.created_by.uuid,
                updated_by=product.updated_by.uuid,
            )
        return ProductDetailsDTO(
            id=product.id.uuid,
            type=product.type,
            variant_id=product.variant.id.uuid,
            sku_id=product.variant.sku_id.uuid,
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
            created_at=product.created_at,
            updated_at=product.updated_at,
            created_by=product.created_by.uuid,
            updated_by=product.updated_by.uuid,
        )


class InMemoryAttributes:
    def __init__(self) -> None:
        self.rows = {}

    async def add(self, attribute) -> None:
        if any(item.code == attribute.code for item in self.rows.values()):
            raise AttributeAlreadyExistsError("Attribute code already exists.")
        self.rows[attribute.id.uuid] = attribute

    async def option_ids(self, attribute_ids):
        return {
            identifier: frozenset(
                option.id.uuid for option in self.rows[identifier].options
            )
            for identifier in attribute_ids
            if identifier in self.rows
        }

    async def get_details(self, attribute_id, locale):
        attribute = self.rows.get(attribute_id.uuid)
        if attribute is None:
            return None
        return AttributeDetailsDTO(
            id=attribute.id.uuid,
            code=attribute.code,
            type="SELECT",
            name=next(
                (item.name for item in attribute.contents if item.locale == locale),
                None,
            ),
            options=tuple(
                AttributeOptionDTO(
                    option.id.uuid,
                    option.code,
                    next(
                        (
                            item.name
                            for item in option.contents
                            if item.locale == locale
                        ),
                        None,
                    ),
                )
                for option in attribute.options
            ),
        )

    async def list_details(self, locale):
        return tuple(
            [
                await self.get_details(type(attribute.id)(identifier), locale)
                for identifier, attribute in sorted(
                    self.rows.items(), key=lambda item: item[1].code
                )
            ]
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
        self.app.state.authorization_service = Mock(can=AsyncMock(return_value=True))
        self.products = InMemoryProducts()
        self.attributes = InMemoryAttributes()
        self.products.option_codes = {}
        self.skus = Mock(get_code=AsyncMock(return_value="SKU-1"))
        self.locales = Mock(is_active=AsyncMock(return_value=True))
        self.app.dependency_overrides[get_optional_request_context] = (
            lambda: self.app.state.test_context
        )
        self.app.dependency_overrides[get_product_repository] = lambda: self.products
        self.app.dependency_overrides[get_product_query_repository] = (
            lambda: self.products
        )
        self.app.dependency_overrides[get_sku_reader] = lambda: self.skus
        self.app.dependency_overrides[get_locale_reader] = lambda: self.locales
        self.app.dependency_overrides[get_attribute_reader] = lambda: self.attributes
        self.app.dependency_overrides[get_attribute_locale_reader] = lambda: self.locales
        self.app.dependency_overrides[get_attribute_repository] = (
            lambda: self.attributes
        )
        self.app.dependency_overrides[get_attribute_query_repository] = (
            lambda: self.attributes
        )
        self.app.include_router(router, prefix="/api/console")
        self.app.include_router(attribute_router, prefix="/api/console")

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
        self.assertEqual(created.json()["content_locales"], [])
        self.assertEqual(created.json()["sku_code"], "SKU-1")
        missing = await self.client.get(self.item, params={"locale": "uk"})
        self.assertEqual(missing.status_code, 200, missing.text)
        self.assertIsNone(missing.json()["content"])
        self.assertEqual(
            set(missing.json()),
            {
                "id",
                "type",
                "variant_id",
                "sku_id",
                "sku_code",
                "requested_locale",
                "content_locales",
                "content",
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
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
        self.app.state.authorization_service.can.return_value = False
        self.assertEqual(
            (
                await self.client.post(
                    self.collection,
                    json={"sku_id": str(self.sku)},
                    headers=self.headers,
                )
            ).status_code,
            403,
        )

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

    async def test_attribute_and_variable_product_contract(self) -> None:
        self.app.state.uuid_generator = Mock(new=Mock(side_effect=uuid4))
        attributes_url = "/api/console/catalog/attributes"
        created_attribute = await self.client.post(
            attributes_url,
            json={
                "code": " CAPSULES ",
                "contents": [{"locale": "uk", "name": " Капсули "}],
                "options": [
                    {
                        "code": code,
                        "contents": [{"locale": "uk", "name": f"{code} капсул"}],
                    }
                    for code in ("100", "200", "500")
                ],
            },
            headers=self.headers,
        )
        self.assertEqual(created_attribute.status_code, 201, created_attribute.text)
        attribute = created_attribute.json()
        self.assertEqual(attribute["code"], "capsules")
        self.assertEqual(
            (
                await self.client.post(
                    attributes_url,
                    json={"code": "capsules", "options": [{"code": "1"}]},
                    headers=self.headers,
                )
            ).status_code,
            409,
        )
        attribute_id = attribute["id"]
        options = attribute["options"]
        self.products.option_codes = {
            UUID(item["id"]): item["code"] for item in options
        }
        listed = await self.client.get(attributes_url, params={"locale": "uk"})
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["items"][0]["name"], "Капсули")
        detail = await self.client.get(
            f"{attributes_url}/{attribute_id}", params={"locale": "uk"}
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["options"][0]["name"], "100 капсул")
        self.assertEqual(
            (
                await self.client.get(
                    f"{attributes_url}/{uuid4()}", params={"locale": "uk"}
                )
            ).status_code,
            404,
        )
        self.assertEqual((await self.client.get(attributes_url)).status_code, 422)
        variable_url = f"{self.collection}/variable"
        sku_ids = [uuid4(), uuid4(), uuid4()]
        sku_codes = {
            identifier: f"SKU-{index}" for index, identifier in enumerate(sku_ids)
        }

        async def get_code(identifier):
            return sku_codes.get(identifier)

        self.skus.get_code.side_effect = get_code
        payload = {
            "variants": [
                {
                    "sku_id": str(sku_id),
                    "selections": [
                        {
                            "attribute_id": attribute_id,
                            "option_id": options[index]["id"],
                        }
                    ],
                }
                for index, sku_id in enumerate(sku_ids)
            ],
            "contents": [{"locale": "uk", "name": "Omega 3"}],
        }
        created = await self.client.post(
            variable_url, json=payload, headers=self.headers
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["type"], "VARIABLE")
        self.assertEqual(len(created.json()["variants"]), 3)
        read = await self.client.get(
            f"{self.collection}/{created.json()['id']}", params={"locale": "uk"}
        )
        self.assertEqual(read.status_code, 200, read.text)
        self.assertEqual(read.json()["type"], "VARIABLE")
        self.assertEqual(len(read.json()["variants"]), 3)
        self.assertEqual(read.json()["content"]["name"], "Omega 3")
        self.assertEqual(
            read.json()["variants"][0]["selections"][0]["attribute_code"], "capsules"
        )
        self.assertEqual(
            (
                await self.client.get(
                    f"{self.collection}/{created.json()['id']}", params={"locale": "ru"}
                )
            ).json()["content"],
            None,
        )
        changed = await self.client.put(
            f"{self.collection}/{created.json()['id']}/contents/ru",
            json={"name": "Омега 3"},
            headers=self.headers,
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        duplicate = {**payload, "variants": [payload["variants"][0]] * 2}
        self.assertEqual(
            (
                await self.client.post(
                    variable_url, json=duplicate, headers=self.headers
                )
            ).status_code,
            422,
        )
        invalid_option = {
            **payload,
            "variants": [
                {
                    **payload["variants"][0],
                    "selections": [
                        {"attribute_id": attribute_id, "option_id": str(uuid4())}
                    ],
                },
                *payload["variants"][1:],
            ],
        }
        self.assertEqual(
            (
                await self.client.post(
                    variable_url, json=invalid_option, headers=self.headers
                )
            ).status_code,
            422,
        )
        self.assertEqual(
            (await self.client.post(variable_url, json=payload)).status_code, 403
        )
        self.assertEqual(
            (
                await self.client.post(
                    variable_url,
                    json={**payload, "tenant_id": str(self.tenant)},
                    headers=self.headers,
                )
            ).status_code,
            422,
        )
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual(
            (
                await self.client.get(attributes_url, params={"locale": "uk"})
            ).status_code,
            401,
        )
        self.assertEqual(
            (
                await self.client.post(variable_url, json=payload, headers=self.headers)
            ).status_code,
            401,
        )
