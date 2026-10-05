"""HTTP-контракты Category с настоящими auth/CSRF dependencies."""

import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.catalog.application.category.command.create_category.dto import (
    CreateCategoryResultDTO,
)
from src.modules.catalog.application.category.command.move_category.dto import (
    MoveCategoryResultDTO,
)
from src.modules.catalog.application.category.command.put_category_content.dto import (
    PutCategoryContentResultDTO,
)
from src.modules.catalog.application.category.query.get_category.dto import (
    CategoryDetailsDTO,
    CategoryTranslationDTO,
)
from src.modules.catalog.application.category.query.list_categories.dto import (
    CategoryListItemDTO,
)
from src.modules.catalog.domain.category.error import (
    CategoryCycleError,
    CategoryIdentifierAlreadyExistsError,
    CategoryInUseError,
    CategoryNotFoundError,
)
from src.modules.catalog.presentation.category.depends import (
    get_create_category_handler,
    get_delete_category_handler,
    get_get_category_handler,
    get_list_categories_handler,
    get_move_category_handler,
    get_put_category_content_handler,
)
from src.modules.catalog.presentation.category.router import router
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.auth.depends import get_optional_request_context
from src.modules.identity.presentation.auth.http.csrf import issue_csrf
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.modules.shared.infrastructure.tokens.in_memory_token_backend import (
    InMemoryTokenBackend,
)
from src.modules.shared.presentation.tokens.depends import TokenManagerDep


class CategoryHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tenant, self.actor, self.category = uuid4(), uuid4(), uuid4()
        self.now = datetime(2026, 10, 5, tzinfo=UTC)
        self.app = FastAPI()
        self.app.state.context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "session", ("member",)),
            None,
            None,
            None,
        )
        self.app.state.token_manager = TokenManager(InMemoryTokenBackend())
        self.app.dependency_overrides[get_optional_request_context] = (
            lambda: self.app.state.context
        )
        self.create = Mock(
            execute=AsyncMock(
                return_value=CreateCategoryResultDTO(
                    self.category,
                    None,
                    ("uk",),
                    self.now,
                    self.now,
                    self.actor,
                    self.actor,
                )
            )
        )
        self.list = Mock(
            execute=AsyncMock(
                return_value=(CategoryListItemDTO(self.category, None, "Назва"),)
            )
        )
        self.get = Mock(
            execute=AsyncMock(
                return_value=CategoryDetailsDTO(
                    self.category,
                    None,
                    "uk",
                    "Назва",
                    (CategoryTranslationDTO("uk", "Назва"),),
                    self.now,
                    self.now,
                    self.actor,
                    self.actor,
                )
            )
        )
        self.put = Mock(
            execute=AsyncMock(
                return_value=PutCategoryContentResultDTO(
                    self.category,
                    "uk",
                    "Назва",
                    self.now,
                    self.actor,
                )
            )
        )
        self.move = Mock(
            execute=AsyncMock(
                return_value=MoveCategoryResultDTO(
                    self.category,
                    None,
                    self.now,
                    self.actor,
                )
            )
        )
        self.delete = Mock(execute=AsyncMock(return_value=None))
        for provider, handler in (
            (get_create_category_handler, self.create),
            (get_list_categories_handler, self.list),
            (get_get_category_handler, self.get),
            (get_put_category_content_handler, self.put),
            (get_move_category_handler, self.move),
            (get_delete_category_handler, self.delete),
        ):
            self.app.dependency_overrides[provider] = lambda handler=handler: handler
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
        self.path = "/api/console/catalog/categories"

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def test_routes_and_payloads(self) -> None:
        created = await self.client.post(
            self.path,
            json={"translations": [{"locale": "uk", "name": "Назва"}]},
            headers=self.headers,
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["locales"], ["uk"])
        listed = await self.client.get(self.path, params={"locale": "uk"})
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()[0]["name"], "Назва")
        fetched = await self.client.get(
            f"{self.path}/{self.category}", params={"locale": "uk"}
        )
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(
            fetched.json()["translations"], [{"locale": "uk", "name": "Назва"}]
        )
        changed = await self.client.put(
            f"{self.path}/{self.category}/contents/uk",
            json={"name": "Назва"},
            headers=self.headers,
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        moved = await self.client.put(
            f"{self.path}/{self.category}/parent",
            json={"parent_id": None},
            headers=self.headers,
        )
        self.assertEqual(moved.status_code, 200, moved.text)
        deleted = await self.client.delete(
            f"{self.path}/{self.category}", headers=self.headers
        )
        self.assertEqual(deleted.status_code, 204, deleted.text)

    async def test_auth_csrf_validation_and_conflicts(self) -> None:
        self.app.state.context = RequestContext(None, None, None, None)
        self.assertEqual(
            (await self.client.get(self.path, params={"locale": "uk"})).status_code, 401
        )
        self.app.state.context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "session", ("member",)),
            None,
            None,
            None,
        )
        self.assertEqual(
            (
                await self.client.post(
                    self.path, json={"translations": [{"locale": "uk", "name": "Name"}]}
                )
            ).status_code,
            403,
        )
        self.assertEqual(
            (
                await self.client.post(
                    self.path,
                    json={"translations": [], "id": str(uuid4())},
                    headers=self.headers,
                )
            ).status_code,
            422,
        )
        self.assertEqual((await self.client.get(self.path)).status_code, 422)
        self.move.execute.side_effect = CategoryCycleError("cycle")
        self.assertEqual(
            (
                await self.client.put(
                    f"{self.path}/{self.category}/parent",
                    json={"parent_id": str(uuid4())},
                    headers=self.headers,
                )
            ).status_code,
            409,
        )
        self.delete.execute.side_effect = CategoryInUseError("in use")
        self.assertEqual(
            (
                await self.client.delete(
                    f"{self.path}/{self.category}", headers=self.headers
                )
            ).status_code,
            409,
        )
        self.create.execute.side_effect = CategoryIdentifierAlreadyExistsError(
            "duplicate"
        )
        self.assertEqual(
            (
                await self.client.post(
                    self.path,
                    json={"translations": [{"locale": "uk", "name": "Name"}]},
                    headers=self.headers,
                )
            ).status_code,
            409,
        )
        self.get.execute.side_effect = CategoryNotFoundError("not found")
        self.assertEqual(
            (
                await self.client.get(
                    f"{self.path}/{self.category}", params={"locale": "uk"}
                )
            ).status_code,
            404,
        )
