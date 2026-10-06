"""HTTP-контракт редактора определений и типов Catalog."""

import unittest
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.catalog.application.content_schema.contracts import (
    BlockDefinitionDTO,
    ProductTypeSchemaDTO,
)
from src.modules.catalog.application.content_schema.service import SchemaConflictError
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)
from src.modules.catalog.presentation.content_schema.depends import (
    get_content_schema_service,
)
from src.modules.catalog.presentation.content_schema.router import (
    blocks_router,
    types_router,
)
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
        self.block = BlockDefinitionDTO(
            self.block_id,
            "ingredients",
            ContentBlockType.RICH_TEXT,
            False,
            {"uk": "Склад"},
        )
        self.product_type = ProductTypeSchemaDTO(
            self.type_id, "vitamins", False, 1, {"uk": "Вітаміни"}, ()
        )
        self.service = Mock(
            create_block=AsyncMock(return_value=self.block),
            list_blocks=AsyncMock(return_value=(self.block,)),
            get_block=AsyncMock(return_value=self.block),
            update_block=AsyncMock(return_value=self.block),
            delete_block=AsyncMock(),
            create_type=AsyncMock(return_value=self.product_type),
            list_types=AsyncMock(return_value=(self.product_type,)),
            get_type=AsyncMock(return_value=self.product_type),
            update_type=AsyncMock(return_value=self.product_type),
            delete_type=AsyncMock(),
        )
        actor, tenant = uuid4(), uuid4()
        self.context = RequestContext(
            Principal(str(actor), str(tenant), "session", ("member",)), None, None, None
        )
        self.app = FastAPI()
        self.app.state.context = self.context
        self.app.state.token_manager = TokenManager(InMemoryTokenBackend())
        self.app.state.clock = Mock(
            now=Mock(return_value=datetime(2026, 10, 6, tzinfo=UTC))
        )
        self.app.dependency_overrides[get_optional_request_context] = (
            lambda: self.app.state.context
        )
        self.app.dependency_overrides[get_content_schema_service] = lambda: self.service
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
        type_url = "/api/console/catalog/product-types"
        created_type = await self.client.post(
            type_url,
            json={"code": "vitamins", "translations": {"uk": "Вітаміни"}, "blocks": []},
            headers=self.headers,
        )
        self.assertEqual(created_type.status_code, 201, created_type.text)
        self.assertEqual(created_type.json()["schema_version"], 1)

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
        self.service.update_type.side_effect = SchemaConflictError(
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
