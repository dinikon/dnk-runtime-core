"""HTTP-контракты самостоятельных ContentBlock и ProductType."""

import unittest
from dataclasses import replace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.catalog.application.content_block.query.get_content_block.dto import (
    ContentBlockDetailsDTO,
)
from src.modules.catalog.application.product_type.port.schema_reader import (
    ProductTypeSchemaDTO,
)
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)
from src.modules.catalog.domain.product_type.error import ProductTypeConflictError
from src.modules.catalog.presentation.content_block.depends import (
    get_create_content_block_handler,
    get_get_content_block_handler,
    get_list_content_blocks_handler,
)
from src.modules.catalog.presentation.product_type.depends import (
    get_create_product_type_handler,
    get_put_product_type_handler,
)
from src.modules.catalog.presentation.content_block.router import (
    router as blocks_router,
)
from src.modules.catalog.presentation.product_type.router import router as types_router
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.auth.depends import get_optional_request_context
from src.modules.identity.presentation.auth.http.csrf import issue_csrf
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.modules.shared.infrastructure.tokens.in_memory_token_backend import (
    InMemoryTokenBackend,
)
from src.modules.shared.presentation.tokens.depends import TokenManagerDep


class ContentSchemaHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.block_id, self.type_id = uuid4(), uuid4()
        block = ContentBlockDetailsDTO(
            self.block_id,
            "ingredients",
            ContentBlockType.RICH_TEXT,
            False,
            {"uk": "Склад"},
        )
        product_type = ProductTypeSchemaDTO(
            self.type_id, "vitamins", False, 1, {"uk": "Вітаміни"}, ()
        )
        self.put_handler = Mock(execute=AsyncMock(return_value=product_type))
        actor, tenant = uuid4(), uuid4()
        self.context = RequestContext(
            Principal(str(actor), str(tenant), "session", ("member",)), None, None, None
        )
        self.app = FastAPI()
        self.app.state.context = self.context
        self.app.state.token_manager = TokenManager(InMemoryTokenBackend())
        self.app.dependency_overrides[get_optional_request_context] = (
            lambda: self.app.state.context
        )
        self.app.dependency_overrides[get_create_content_block_handler] = lambda: Mock(
            execute=AsyncMock(return_value=block)
        )
        self.app.dependency_overrides[get_get_content_block_handler] = lambda: Mock(
            execute=AsyncMock(return_value=block)
        )
        self.app.dependency_overrides[get_list_content_blocks_handler] = lambda: Mock(
            execute=AsyncMock(return_value=(block,))
        )
        self.app.dependency_overrides[get_create_product_type_handler] = lambda: Mock(
            execute=AsyncMock(return_value=product_type)
        )
        self.app.dependency_overrides[get_put_product_type_handler] = (
            lambda: self.put_handler
        )
        self.app.include_router(blocks_router, prefix="/api/console")
        self.app.include_router(types_router, prefix="/api/console")

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

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_create_and_read_both_schemas(self) -> None:
        block_url = "/api/console/catalog/content-blocks"
        created = await self.client.post(
            block_url,
            json={
                "code": "ingredients",
                "type": "rich_text",
                "translations": {"uk": "Склад"},
            },
            headers=self.headers,
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["code"], "ingredients")
        self.assertEqual(
            (await self.client.get(block_url)).json()[0]["id"], str(self.block_id)
        )
        self.assertEqual(
            (await self.client.get(f"{block_url}/{self.block_id}")).status_code, 200
        )
        created_type = await self.client.post(
            "/api/console/catalog/product-types",
            json={"code": "vitamins", "translations": {"uk": "Вітаміни"}, "blocks": []},
            headers=self.headers,
        )
        self.assertEqual(created_type.status_code, 201, created_type.text)
        self.assertEqual(created_type.json()["schema_version"], 1)

    async def test_type_accepts_block_uuid_strings_in_two_scopes(self) -> None:
        result = await self.client.post(
            "/api/console/catalog/product-types",
            json={
                "code": "vitamins",
                "translations": {"uk": "Вітаміни"},
                "blocks": [
                    {
                        "block_id": str(self.block_id),
                        "scope": scope,
                        "required": scope == "product",
                        "position": 0,
                    }
                    for scope in ("product", "variant")
                ],
            },
            headers=self.headers,
        )
        self.assertEqual(result.status_code, 201, result.text)

    async def test_auth_csrf_validation_and_conflict(self) -> None:
        url = "/api/console/catalog/content-blocks"
        self.app.state.context = replace(self.context, principal=None)
        self.assertEqual((await self.client.get(url)).status_code, 401)
        self.app.state.context = self.context
        payload = {
            "code": "ingredients",
            "type": "rich_text",
            "translations": {"uk": "Склад"},
        }
        self.assertEqual((await self.client.post(url, json=payload)).status_code, 403)
        self.assertEqual(
            (
                await self.client.post(
                    url, json={**payload, "scope": "product"}, headers=self.headers
                )
            ).status_code,
            422,
        )
        self.put_handler.execute.side_effect = ProductTypeConflictError(
            "Product type schema version changed."
        )
        result = await self.client.put(
            f"/api/console/catalog/product-types/{self.type_id}",
            json={
                "expected_schema_version": 0,
                "translations": {"uk": "Вітаміни"},
                "blocks": [],
            },
            headers=self.headers,
        )
        self.assertEqual(result.status_code, 409, result.text)
