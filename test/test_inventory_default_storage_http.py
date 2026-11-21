"""HTTP-контракт назначения основной STORAGE с настоящими auth, CSRF и Domain."""

from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.inventory.application.warehouse.command.set_default_storage_location.handler import (
    SetDefaultStorageLocationHandler,
)
from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.value_object.code import LocationCodeVO
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_location.value_object.name import LocationNameVO
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO
from src.modules.inventory.presentation.warehouse.depends import (
    get_set_default_storage_location_handler,
)
from src.modules.inventory.presentation.warehouse.router import router
from test.inventory_item_support import inventory_item_app


class DefaultStorageHttpTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет транспортную валидацию отдельно от Domain-правил и сборки БД."""

    async def asyncSetUp(self) -> None:
        """Собирает router с реальным handler на наблюдаемых write-портах."""
        self.context = RequestContext(
            Principal(str(uuid4()), str(uuid4()), "session", ("member",)),
            None,
            None,
            None,
        )
        self.warehouse = Warehouse.create(
            identifier=WarehouseIdVO(uuid4()),
            code=WarehouseCodeVO("main"),
            name=WarehouseNameVO("Склад"),
        )
        self.location = StockLocation.create(
            identifier=StockLocationIdVO(uuid4()),
            warehouse=self.warehouse.snapshot(),
            code=LocationCodeVO("new"),
            name=LocationNameVO("Новая основная"),
            location_type=LocationType.STORAGE,
        )
        self.warehouses = Mock(
            get_for_update=AsyncMock(return_value=self.warehouse), save=AsyncMock()
        )
        self.locations = Mock(get_for_update=AsyncMock(return_value=self.location))
        real_handler = SetDefaultStorageLocationHandler(self.warehouses, self.locations)
        self.handler = Mock(execute=AsyncMock(wraps=real_handler.execute))
        self.app = inventory_item_app(Mock(), self.context)
        self.app.include_router(router, prefix="/api/console")
        self.app.dependency_overrides[get_set_default_storage_location_handler] = (
            lambda: self.handler
        )
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=origin,
        )
        self.addAsyncCleanup(self.client.aclose)
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": origin, "X-CSRF-Token": token}
        self.url = f"/api/console/inventory/warehouses/{self.warehouse.id.uuid}/default-storage-location"
        self.payload = {"location_id": str(self.location.id.uuid)}

    async def test_put_returns_specific_warehouse_response_and_typed_command(
        self,
    ) -> None:
        """Передаёт UUID как VO, возвращает карточку и отдельную OpenAPI-схему."""
        response = await self.client.put(
            self.url, headers=self.headers, json=self.payload
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {
                "id": str(self.warehouse.id.uuid),
                "code": "main",
                "name": "Склад",
                "is_active": True,
                "default_storage_location_id": str(self.location.id.uuid),
            },
        )
        command = self.handler.execute.await_args.args[0]
        self.assertEqual(
            (command.warehouse_id, command.location_id),
            (self.warehouse.id, self.location.id),
        )
        schema = self.app.openapi()["paths"][
            "/api/console/inventory/warehouses/{warehouse_id}/default-storage-location"
        ]["put"]
        self.assertEqual(
            schema["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/SetDefaultStorageLocationResponse",
        )

    async def test_request_validation_happens_before_application(self) -> None:
        """Отклоняет пустоту, null, некорректный UUID, типы и неизвестные поля до handler."""
        invalid = [
            {},
            {"location_id": None},
            {"location_id": ""},
            {"location_id": "bad"},
            {"location_id": False},
            {"location_id": 1},
            {"location_id": []},
            {**self.payload, "warehouse_id": str(self.warehouse.id.uuid)},
            {**self.payload, "default_storage_location_id": str(uuid4())},
            {**self.payload, "is_active": True},
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                response = await self.client.put(
                    self.url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, 422, response.text)
        response = await self.client.put(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 422, response.text)
        response = await self.client.put(
            self.url.replace(str(self.warehouse.id.uuid), "bad"),
            headers=self.headers,
            json=self.payload,
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.handler.execute.assert_not_awaited()
        self.warehouses.get_for_update.assert_not_awaited()

    async def test_missing_references_and_domain_rejections_have_distinct_status(
        self,
    ) -> None:
        """Отсутствующие ссылки дают 404, неверные тип и активность локации — 422."""
        self.warehouses.get_for_update.return_value = None
        response = await self.client.put(
            self.url, headers=self.headers, json=self.payload
        )
        self.assertEqual(response.status_code, 404, response.text)
        self.warehouses.get_for_update.return_value = self.warehouse
        self.locations.get_for_update.return_value = None
        response = await self.client.put(
            self.url, headers=self.headers, json=self.payload
        )
        self.assertEqual(response.status_code, 404, response.text)
        for location in (
            replace(self.location, location_type=LocationType.TRANSIT),
            replace(self.location, is_active=False),
        ):
            self.locations.get_for_update.return_value = location
            response = await self.client.put(
                self.url, headers=self.headers, json=self.payload
            )
            self.assertEqual(response.status_code, 422, response.text)
        self.warehouses.save.assert_not_awaited()

    async def test_security_rejects_before_handler(self) -> None:
        """Требует CSRF с правильным Origin, principal и tenant."""
        for headers in (
            {},
            {**self.headers, "X-CSRF-Token": "invalid"},
            {**self.headers, "Origin": "https://other.example"},
        ):
            response = await self.client.put(
                self.url, headers=headers, json=self.payload
            )
            self.assertEqual(response.status_code, 403, response.text)
        for principal, expected in (
            (None, 401),
            (replace(self.context.principal, tenant_id=None), 403),
        ):
            self.app.state.test_context = replace(self.context, principal=principal)
            response = await self.client.put(
                self.url, headers=self.headers, json=self.payload
            )
            self.assertEqual(response.status_code, expected, response.text)
        self.handler.execute.assert_not_awaited()

    async def test_inactive_warehouse_is_not_activated(self) -> None:
        """Справочная операция сохраняет false в ответе и в записанном агрегате."""
        self.warehouses.get_for_update.return_value = self.warehouse.deactivate()
        response = await self.client.put(
            self.url, headers=self.headers, json=self.payload
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["is_active"])
        self.assertFalse(self.warehouses.save.await_args.args[0].is_active)

    async def test_technical_write_failure_does_not_return_200(self) -> None:
        """Не скрывает неожиданный отказ записи за успешным HTTP-результатом."""
        self.warehouses.save.side_effect = RuntimeError("storage unavailable")
        response = await self.client.put(
            self.url, headers=self.headers, json=self.payload
        )
        self.assertEqual(response.status_code, 500, response.text)
