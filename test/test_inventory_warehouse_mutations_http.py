"""Валидация PUT/PATCH Warehouse в Presentation без подключения PostgreSQL."""

import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.inventory.application.warehouse.command.update_warehouse.handler import (
    UpdateWarehouseHandler,
)
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO
from src.modules.inventory.presentation.warehouse.depends import (
    get_update_warehouse_handler,
)
from src.modules.inventory.presentation.warehouse.router import router
from test.inventory_item_support import inventory_item_app


class WarehouseMutationHttpTests(unittest.IsolatedAsyncioTestCase):
    """Использует реальные request schemas, handler и Domain с тестовым write-портом."""

    async def asyncSetUp(self) -> None:
        """Собирает HTTP-приложение с auth/CSRF и наблюдаемым обработчиком."""
        context = RequestContext(
            Principal(str(uuid4()), str(uuid4()), "session", ("member",)),
            None,
            None,
            None,
        )
        self.warehouse = Warehouse.restore(
            identifier=WarehouseIdVO(uuid4()),
            code=WarehouseCodeVO("original"),
            name=WarehouseNameVO("Name"),
            is_active=True,
            default_storage_location_id=None,
        )
        self.repository = Mock(
            get_for_update=AsyncMock(return_value=self.warehouse), save=AsyncMock()
        )
        handler = UpdateWarehouseHandler(self.repository)
        self.handler = Mock(execute=AsyncMock(wraps=handler.execute))
        app = inventory_item_app(Mock(), context)
        app.include_router(router, prefix="/api/console")
        app.dependency_overrides[get_update_warehouse_handler] = lambda: self.handler
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url=origin,
        )
        self.addAsyncCleanup(self.client.aclose)
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": token}
        self.url = f"/api/console/inventory/warehouses/{self.warehouse.id.uuid}"
        self.full = {"code": "updated", "name": "Updated", "is_active": False}

    async def test_request_schema_rejects_invalid_payload_before_handler(self) -> None:
        """Пустота, null, неизвестные поля и неверные типы дают 422 до Application."""
        invalid = [
            {"unknown": "value"},
            {"default_storage_location_id": str(uuid4())},
            {"code": None},
            {"name": None},
            {"is_active": None},
            {"code": 123},
            {"name": False},
            {"is_active": 0},
            {"is_active": 1},
            {"is_active": "false"},
        ]
        for method in ("PUT", "PATCH"):
            payloads = [
                values if method == "PATCH" else {**self.full, **values}
                for values in invalid
            ]
            payloads.append({})
            if method == "PUT":
                payloads.extend(
                    {key: value for key, value in self.full.items() if key != field}
                    for field in self.full
                )
            for payload in payloads:
                with self.subTest(method=method, payload=payload):
                    response = await self.client.request(
                        method, self.url, headers=self.headers, json=payload
                    )
                    self.assertEqual(response.status_code, 422, response.text)
        self.handler.execute.assert_not_awaited()
        self.repository.get_for_update.assert_not_awaited()
        self.repository.save.assert_not_awaited()

    async def test_patch_preserves_explicit_false_and_omitted_fields(self) -> None:
        """Валидный false доходит до Domain, остальные значения не изменяются."""
        response = await self.client.patch(
            self.url, headers=self.headers, json={"is_active": False}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            (
                response.json()["code"],
                response.json()["name"],
                response.json()["is_active"],
            ),
            ("original", "Name", False),
        )
        command = self.handler.execute.await_args.args[0]
        self.assertEqual(command.fields, frozenset({"is_active"}))
        self.assertIs(command.is_active, False)
        self.repository.save.assert_awaited_once()
        self.assertTrue(self.warehouse.is_active)

    async def test_put_applies_complete_configuration_through_domain(self) -> None:
        """Полное представление нормализуется доменными VO и сохраняет false."""
        response = await self.client.put(
            self.url,
            headers=self.headers,
            json={**self.full, "code": " UPDATED ", "name": " Updated "},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            (
                response.json()["code"],
                response.json()["name"],
                response.json()["is_active"],
            ),
            ("updated", "Updated", False),
        )
        self.assertEqual(
            self.handler.execute.await_args.args[0].fields,
            frozenset({"code", "name", "is_active"}),
        )
        self.repository.save.assert_awaited_once()

    async def test_invalid_domain_values_still_return_422(self) -> None:
        """Структурно корректный запрос делегирует проверку значений Domain."""
        for payload in ({"code": " "}, {"name": "\u200bName"}):
            with self.subTest(payload=payload):
                response = await self.client.patch(
                    self.url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.handler.execute.await_count, 2)
        self.repository.save.assert_not_awaited()
