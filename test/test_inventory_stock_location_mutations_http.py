"""Контракты PUT/PATCH локаций с Pydantic и реальным handler без PostgreSQL."""

from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.modules.inventory.application.stock_location.command.update_stock_location.handler import (
    UpdateStockLocationHandler,
)
from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.domain.stock_location.error import (
    StockLocationCodeAlreadyExistsError,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.code import LocationCodeVO
from src.modules.inventory.domain.stock_location.value_object.name import LocationNameVO
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from test import test_inventory_stock_location_http as support


class StockLocationMutationsHttpTests(unittest.IsolatedAsyncioTestCase):
    """Повторно использует изолированные HTTP-порты создания без наследования тестов."""

    async def asyncSetUp(self) -> None:
        """Готовит изменяемую карточку и наблюдаемый write-порт общего handler."""
        await support.StockLocationHttpTests.asyncSetUp(self)
        self.location = StockLocation.create(
            identifier=StockLocationIdVO(self.location_id),
            warehouse=self.warehouse.snapshot(),
            code=LocationCodeVO("original"),
            name=LocationNameVO("Original"),
            location_type=LocationType.STORAGE,
        )
        self.locations.get_for_update = AsyncMock(return_value=self.location)
        self.locations.save = AsyncMock()
        self.url = f"{self.url}/{self.location_id}"
        self.full = {"code": "original", "name": "Original", "is_active": True}

    async def test_put_patch_fields_false_and_separate_response_contracts(self) -> None:
        """PUT передаёт все три поля, PATCH сохраняет набор полей и явное false."""
        response = await self.client.put(
            self.url,
            headers=self.headers,
            json={"code": " NEW ", "name": " New Name ", "is_active": False},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {
                "id": str(self.location_id),
                "warehouse_id": str(self.warehouse.id.uuid),
                "parent_location_id": None,
                "code": "new",
                "name": "New Name",
                "location_type": "STORAGE",
                "is_active": False,
            },
        )
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
            ("original", "Original", False),
        )
        schema = self.app.openapi()
        path = (
            "/api/console/inventory/warehouses/{warehouse_id}/locations/{location_id}"
        )
        for method, ref in [
            ("put", "PutStockLocationResponse"),
            ("patch", "PatchStockLocationResponse"),
        ]:
            self.assertEqual(
                schema["paths"][path][method]["responses"]["200"]["content"][
                    "application/json"
                ]["schema"]["$ref"],
                f"#/components/schemas/{ref}",
            )

    async def test_request_schemas_reject_structure_before_application(self) -> None:
        """Неполный PUT, пустой PATCH, null, типы и фиксированные поля дают 422 до handler."""
        invalid = [
            {"code": None},
            {"name": None},
            {"is_active": None},
            {"code": 123},
            {"name": False},
            {"is_active": 0},
            {"is_active": 1},
            {"is_active": "false"},
            *(
                {key: value}
                for key, value in [
                    ("unknown", 1),
                    ("id", str(uuid4())),
                    ("warehouse_id", str(uuid4())),
                    ("parent_location_id", None),
                    ("location_type", "STORAGE"),
                    ("version", 1),
                ]
            ),
        ]
        with patch.object(
            UpdateStockLocationHandler, "execute", new_callable=AsyncMock
        ) as execute:
            for method in ("PUT", "PATCH"):
                payloads = [
                    value if method == "PATCH" else {**self.full, **value}
                    for value in invalid
                ] + [{}]
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
            execute.assert_not_awaited()
        self.warehouses.get_for_share.assert_not_awaited()
        self.locations.save.assert_not_awaited()

    async def test_main_storage_conflict_and_domain_values_have_distinct_status(
        self,
    ) -> None:
        """Защита основной STORAGE даёт 409, ошибка VO — 422, ввод не сохраняется частично."""
        self.warehouses.get_for_share.return_value = (
            self.warehouse.set_default_storage_location(self.location.snapshot())
        )
        for method in ("PUT", "PATCH"):
            response = await self.client.request(
                method,
                self.url,
                headers=self.headers,
                json={**self.full, "name": "Must roll back", "is_active": False},
            )
            self.assertEqual(response.status_code, 409, response.text)
        self.locations.save.assert_not_awaited()
        response = await self.client.patch(
            self.url, headers=self.headers, json={"code": " "}
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.locations.save.side_effect = StockLocationCodeAlreadyExistsError(
            "duplicate"
        )
        response = await self.client.patch(
            self.url, headers=self.headers, json={"code": "duplicate"}
        )
        self.assertEqual(response.status_code, 409, response.text)

    async def test_missing_context_and_paths_never_invoke_handler(self) -> None:
        """Оба метода требуют auth/tenant/CSRF и типизированные UUID маршрута."""
        for method in ("PUT", "PATCH"):
            self.assertEqual(
                (
                    await self.client.request(method, self.url, json=self.full)
                ).status_code,
                403,
            )
            for principal, expected in (
                (None, 401),
                (replace(self.context.principal, tenant_id=None), 403),
            ):
                self.app.state.test_context = replace(self.context, principal=principal)
                response = await self.client.request(
                    method, self.url, headers=self.headers, json=self.full
                )
                self.assertEqual(response.status_code, expected, response.text)
            self.app.state.test_context = self.context
            for path in (
                self.url.rsplit("/", 1)[0] + "/bad",
                "/api/console/inventory/warehouses/bad/locations/"
                + str(self.location_id),
            ):
                response = await self.client.request(
                    method, path, headers=self.headers, json=self.full
                )
                self.assertEqual(response.status_code, 422, response.text)
        self.warehouses.get_for_share.assert_not_awaited()

    async def test_missing_records_return_404_without_upsert(self) -> None:
        """Отсутствие склада или адреса не сохраняет новую карточку."""
        for method in ("PUT", "PATCH"):
            self.warehouses.get_for_share.return_value = None
            response = await self.client.request(
                method, self.url, headers=self.headers, json=self.full
            )
            self.assertEqual(response.status_code, 404, response.text)
            self.warehouses.get_for_share.return_value = self.warehouse
            self.locations.get_for_update.return_value = None
            response = await self.client.request(
                method, self.url, headers=self.headers, json=self.full
            )
            self.assertEqual(response.status_code, 404, response.text)
        self.locations.save.assert_not_awaited()
