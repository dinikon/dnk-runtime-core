"""HTTP-проверки Warehousing с реальными Depends, UoW и CSRF."""

from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.identity.presentation.auth.depends import get_optional_request_context
from src.modules.identity.presentation.auth.http.csrf import issue_csrf
from src.modules.shared.application.tokens.token_manager import TokenManager
from src.modules.shared.infrastructure.tokens.in_memory_token_backend import (
    InMemoryTokenBackend,
)
from src.modules.shared.presentation.tokens.depends import TokenManagerDep
from src.modules.warehousing.infrastructure.warehouse.persistence.mapper import (
    WarehouseMapper,
)
from src.modules.warehousing.presentation.router import router
from test.test_warehousing import warehouse


class WarehousingHttpTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет публичные контракты, доверенный контекст и итог транзакции."""

    async def asyncSetUp(self) -> None:
        """Собирает production dependencies на одной управляемой тестовой session."""
        self.tenant, self.actor = uuid4(), uuid4()
        self.row = WarehouseMapper.to_insert_values(warehouse())
        self.row.update(created_by=self.actor, updated_by=self.actor)
        self.result = MagicMock()
        self.result.scalar_one_or_none.return_value = self.row["id"]
        self.result.mappings.return_value.one_or_none.return_value = self.row
        self.result.mappings.return_value.__iter__.side_effect = lambda: iter(
            [self.row]
        )
        self.session = SimpleNamespace(
            execute=AsyncMock(return_value=self.result),
            scalar=AsyncMock(return_value="Europe/Kyiv"),
            commit=AsyncMock(),
            rollback=AsyncMock(),
            close=AsyncMock(),
        )
        self.sessions = Mock(return_value=self.session)
        self.authorization = Mock(can=AsyncMock(return_value=True))
        self.app = FastAPI()
        self.app.state.db = self.sessions
        self.app.state.clock = Mock(now=Mock(return_value=self.row["created_at"]))
        self.app.state.uuid_generator = Mock(new=Mock(return_value=self.row["id"]))
        self.app.state.authorization_service = self.authorization
        self.app.state.token_manager = TokenManager(InMemoryTokenBackend())
        self.app.state.context = RequestContext(
            Principal(str(self.actor), str(self.tenant), "session", ("member",)),
            None,
            None,
            None,
        )
        self.app.dependency_overrides[get_optional_request_context] = (
            lambda: self.app.state.context
        )
        self.app.include_router(router, prefix="/api/console")

        @self.app.get("/csrf")
        async def csrf(
            request: Request, response: Response, tokens: TokenManagerDep
        ) -> dict[str, str]:
            """Выдаёт настоящий CSRF-токен тестового browser-контекста."""
            return await issue_csrf(request, response, tokens)

        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}
        self.url = "/api/console/warehousing/warehouses"
        self.payload = {
            "code": " wh-01 ",
            "title": "Склад",
            "type": "storage",
            "policy": {"timezone": "Europe/Kyiv"},
        }

    async def asyncTearDown(self) -> None:
        """Закрывает HTTP-клиент после каждого независимого сценария."""
        await self.client.aclose()

    async def test_create_uses_trusted_actor_and_one_uow_for_catalog_and_insert(
        self,
    ) -> None:
        """POST нормализует код, проверяет справочник и сохраняет аудит одной транзакцией."""
        response = await self.client.post(
            self.url, json=self.payload, headers=self.headers
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(
            response.json(),
            {
                "id": str(self.row["id"]),
                "code": "WH-01",
                "status": "active",
                "revision": 1,
            },
        )
        self.sessions.assert_called_once()
        self.session.scalar.assert_awaited_once()
        self.session.execute.assert_awaited_once()
        values = self.session.execute.await_args.args[0].compile().params
        self.assertEqual(
            (values["created_by"], values["updated_by"]), (self.actor, self.actor)
        )
        self.assertEqual(values["timezone"], "Europe/Kyiv")
        self.authorization.can.assert_awaited_once_with(
            user_id=self.actor,
            tenant_id=self.tenant,
            action="create",
            resource_type="warehouse",
        )
        self.session.commit.assert_awaited_once()
        self.session.rollback.assert_not_awaited()
        self.session.close.assert_awaited_once()

    async def test_get_and_list_return_independent_projections(self) -> None:
        """Карточка содержит собственные policy/аудит, список — страницу и next_cursor."""
        detail = await self.client.get(self.url + "/" + str(self.row["id"]))
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["policy"], {"timezone": "Europe/Kyiv"})
        self.assertEqual(detail.json()["created_by"], str(self.actor))
        self.assertTrue(detail.json()["created_at"].endswith("Z"))
        self.authorization.can.assert_awaited_with(
            user_id=self.actor,
            tenant_id=self.tenant,
            action="read",
            resource_type="warehouse",
            resource_id=self.row["id"],
        )
        page = await self.client.get(
            self.url, params={"status": "active", "type": "storage", "limit": 1}
        )
        self.assertEqual(page.status_code, 200, page.text)
        self.assertEqual(set(page.json()), {"items", "next_cursor"})
        self.assertEqual(page.json()["items"][0]["code"], "WH-01")
        self.assertNotIn("policy", page.json()["items"][0])
        self.assertIsNone(page.json()["next_cursor"])
        self.authorization.can.assert_awaited_with(
            user_id=self.actor,
            tenant_id=self.tenant,
            action="list",
            resource_type="warehouse",
        )

    async def test_not_found_and_duplicate_have_stable_error_codes(self) -> None:
        """Отсутствие склада даёт 404, занятый нормализованный код — 409 с rollback."""
        self.result.mappings.return_value.one_or_none.return_value = None
        missing = await self.client.get(self.url + "/" + str(uuid4()))
        self.assertEqual(
            (missing.status_code, missing.json()["detail"]["code"]),
            (404, "warehouse.not_found"),
        )
        self.result.scalar_one_or_none.return_value = None
        duplicate = await self.client.post(
            self.url, json=self.payload, headers=self.headers
        )
        self.assertEqual(
            (duplicate.status_code, duplicate.json()["detail"]["code"]),
            (409, "warehouse.code_already_exists"),
        )
        self.session.commit.assert_not_awaited()
        self.assertEqual(self.session.rollback.await_count, 2)

    async def test_invalid_timezone_and_values_do_not_insert(self) -> None:
        """Некорректные значения и неактивный timezone отклоняются до INSERT."""
        for field, value, code in (
            ("code", " ", "warehouse.invalid_code"),
            ("title", "x" * 256, "warehouse.invalid_title"),
            ("type", "", "warehouse.invalid_type"),
        ):
            response = await self.client.post(
                self.url, json={**self.payload, field: value}, headers=self.headers
            )
            self.assertEqual(
                (response.status_code, response.json()["detail"]["code"]), (422, code)
            )
        self.session.scalar.return_value = None
        response = await self.client.post(
            self.url, json=self.payload, headers=self.headers
        )
        self.assertEqual(
            (response.status_code, response.json()["detail"]["code"]),
            (422, "warehouse.invalid_timezone"),
        )
        self.session.execute.assert_not_awaited()
        self.session.commit.assert_not_awaited()

    async def test_request_contract_forbids_forged_context_and_settings(self) -> None:
        """Контекст, статус, ревизия и произвольная policy не принимаются из тела."""
        for field in ("tenant_id", "actor_id", "status", "revision", "id", "owner_id"):
            response = await self.client.post(
                self.url, json={**self.payload, field: "forged"}, headers=self.headers
            )
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual(response.json()["detail"][0]["type"], "extra_forbidden")
        for payload in (
            {**self.payload, "code": 123},
            {**self.payload, "policy": {}},
            {**self.payload, "policy": {"timezone": "Europe/Kyiv", "capacity": 10}},
        ):
            response = await self.client.post(
                self.url, json=payload, headers=self.headers
            )
            self.assertEqual(response.status_code, 422, response.text)
        self.session.execute.assert_not_awaited()

    async def test_authentication_tenant_authorization_and_csrf(self) -> None:
        """Все три метода требуют аутентификацию и права; POST также проверяет CSRF."""
        response = await self.client.post(self.url, json=self.payload)
        self.assertEqual(response.status_code, 403)
        self.authorization.can.return_value = False
        for method, url in (
            ("post", self.url),
            ("get", self.url),
            ("get", self.url + "/" + str(uuid4())),
        ):
            kwargs = (
                {"json": self.payload, "headers": self.headers}
                if method == "post"
                else {}
            )
            response = await getattr(self.client, method)(url, **kwargs)
            self.assertEqual(
                (response.status_code, response.json()["detail"]["code"]),
                (403, "warehouse.forbidden"),
            )
        self.authorization.can.return_value = True
        original = self.app.state.context
        self.app.state.context = replace(
            original, principal=replace(original.principal, tenant_id=None)
        )
        response = await self.client.get(self.url)
        self.assertEqual(
            (response.status_code, response.json()["detail"]["code"]),
            (403, "warehouse.tenant_required"),
        )
        self.app.state.context = replace(original, principal=None)
        response = await self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
        self.session.execute.assert_not_awaited()
        self.session.scalar.assert_not_awaited()

    async def test_invalid_query_parameters(self) -> None:
        """Неверные UUID, status, type, cursor и limit дают 422 до чтения проекций."""
        for params in (
            {"status": "unknown"},
            {"type": " "},
            {"cursor": "!"},
            {"limit": 0},
            {"limit": 101},
            {"limit": "abc"},
        ):
            response = await self.client.get(self.url, params=params)
            self.assertEqual(response.status_code, 422, response.text)
        response = await self.client.get(self.url + "/bad-uuid")
        self.assertEqual(response.status_code, 422)
        self.session.execute.assert_not_awaited()

    async def test_commit_failure_cannot_return_created(self) -> None:
        """Сбой commit после INSERT превращает запрос в 500 и закрывает session."""
        self.session.commit.side_effect = RuntimeError("injected commit failure")
        with self.assertLogs(
            "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
            level="ERROR",
        ):
            response = await self.client.post(
                self.url, json=self.payload, headers=self.headers
            )
        self.assertEqual(response.status_code, 500)
        self.session.rollback.assert_awaited_once()
        self.session.close.assert_awaited_once()

    def test_openapi_has_three_independent_method_contracts(self) -> None:
        """GET не имеют Request; каждый метод возвращает собственную HTTP-схему."""
        schema = self.app.openapi()
        for path, method, response in (
            (self.url, "post", "CreateWarehouseResponse"),
            (self.url, "get", "ListWarehousesResponse"),
            (self.url + "/{warehouse_id}", "get", "GetWarehouseResponse"),
        ):
            operation = schema["paths"][path][method]
            self.assertEqual("requestBody" in operation, method == "post")
            success = operation["responses"]["201" if method == "post" else "200"]
            self.assertEqual(
                success["content"]["application/json"]["schema"]["$ref"],
                "#/components/schemas/" + response,
            )
