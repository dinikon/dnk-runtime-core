"""HTTP-контракты локаций с настоящими Pydantic-схемами и handlers без SQL."""

from dataclasses import replace
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.inventory.application.stock_location.command.create_stock_location.handler import (
    CreateStockLocationHandler,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.handler import (
    ListStockLocationsHandler,
)
from src.modules.inventory.application.stock_location.query.get_stock_location.dto import (
    GetStockLocationResultDTO,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.dto import (
    ListStockLocationsResultDTO,
    StockLocationListItemDTO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_location.error import (
    StockLocationCodeAlreadyExistsError,
)
from src.modules.inventory.domain.warehouse.aggregate import Warehouse
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.value_object.code import WarehouseCodeVO
from src.modules.inventory.domain.warehouse.value_object.name import WarehouseNameVO
from src.modules.inventory.presentation.stock_location.depends import (
    get_stock_location_repository,
    get_stock_location_query_repository,
)
from src.modules.inventory.presentation.warehouse.depends import (
    get_warehouse_repository,
)
from src.modules.inventory.presentation.stock_location.router import router
from test.inventory_item_support import inventory_item_app


class StockLocationHttpTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет границу валидации, статусы, сериализацию и auth/CSRF."""

    async def asyncSetUp(self) -> None:
        """Собирает приложение с изолированными портами и настоящим CSRF."""
        self.context = RequestContext(
            Principal(str(uuid4()), str(uuid4()), "session", ("member",)),
            None,
            None,
            None,
        )
        self.warehouse = Warehouse.create(
            identifier=WarehouseIdVO(uuid4()),
            code=WarehouseCodeVO("main"),
            name=WarehouseNameVO("Main"),
        )
        self.warehouses = Mock(get_for_share=AsyncMock(return_value=self.warehouse))
        self.locations = Mock(get=AsyncMock(return_value=None), add=AsyncMock())
        self.location_id = uuid4()
        detail = GetStockLocationResultDTO(
            self.location_id,
            self.warehouse.id.uuid,
            None,
            "storage",
            "Storage",
            LocationType.STORAGE,
            True,
        )
        row = StockLocationListItemDTO(
            detail.id,
            detail.warehouse_id,
            detail.parent_location_id,
            detail.code,
            detail.name,
            detail.location_type,
            detail.is_active,
        )
        self.queries = Mock(
            warehouse_exists=AsyncMock(return_value=True),
            get_details=AsyncMock(return_value=detail),
            list=AsyncMock(return_value=ListStockLocationsResultDTO((row,), 1, 0, 50)),
        )
        self.app = inventory_item_app(Mock(), self.context)
        self.app.include_router(router, prefix="/api/console")
        self.app.state.uuid_generator = Mock(new=Mock(return_value=self.location_id))
        self.app.dependency_overrides[get_warehouse_repository] = (
            lambda: self.warehouses
        )
        self.app.dependency_overrides[get_stock_location_repository] = (
            lambda: self.locations
        )
        self.app.dependency_overrides[get_stock_location_query_repository] = (
            lambda: self.queries
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
        self.url = (
            f"/api/console/inventory/warehouses/{self.warehouse.id.uuid}/locations"
        )
        self.payload = {
            "code": " A-001 ",
            "name": " Address ",
            "location_type": "STORAGE",
        }

    async def test_create_card_and_list_have_separate_complete_contracts(self) -> None:
        """Возвращает канонические поля, null родителя и страницу с metadata."""
        response = await self.client.post(
            self.url, headers=self.headers, json=self.payload
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(
            response.json(),
            {
                "id": str(self.location_id),
                "warehouse_id": str(self.warehouse.id.uuid),
                "parent_location_id": None,
                "code": "a-001",
                "name": "Address",
                "location_type": "STORAGE",
                "is_active": True,
            },
        )
        self.assertEqual(
            (await self.client.get(f"{self.url}/{self.location_id}")).status_code, 200
        )
        response = await self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            (
                response.json()["total"],
                response.json()["offset"],
                response.json()["limit"],
            ),
            (1, 0, 50),
        )
        schema = self.app.openapi()
        path = "/api/console/inventory/warehouses/{warehouse_id}/locations"
        self.assertEqual(set(schema["paths"][path]), {"get", "post"})
        self.assertEqual(
            schema["paths"][path]["post"]["responses"]["201"]["content"][
                "application/json"
            ]["schema"]["$ref"],
            "#/components/schemas/CreateStockLocationResponse",
        )

    async def test_invalid_post_is_rejected_before_application(self) -> None:
        """Pydantic отклоняет неполноту, null, типы, UUID и неизвестные поля."""
        invalid = [
            {},
            *(
                {k: v for k, v in self.payload.items() if k != field}
                for field in self.payload
            ),
            *({**self.payload, field: None} for field in self.payload),
            {**self.payload, "code": 1},
            {**self.payload, "name": False},
            {**self.payload, "location_type": "UNKNOWN"},
            {**self.payload, "parent_location_id": "bad"},
            *(
                {**self.payload, field: value}
                for field, value in [
                    ("warehouse_id", str(uuid4())),
                    ("id", str(uuid4())),
                    ("is_active", False),
                    ("unknown", 1),
                ]
            ),
        ]
        with patch.object(
            CreateStockLocationHandler, "execute", new_callable=AsyncMock
        ) as execute:
            for payload in invalid:
                with self.subTest(payload=payload):
                    response = await self.client.post(
                        self.url, headers=self.headers, json=payload
                    )
                    self.assertEqual(response.status_code, 422, response.text)
            execute.assert_not_awaited()
        self.locations.add.assert_not_awaited()

    async def test_query_schema_validates_and_preserves_false(self) -> None:
        """GET валидирует enum/UUID/пагинацию до handler и не теряет фильтр false."""
        invalid = [
            {"offset": -1},
            {"offset": 2_147_483_648},
            {"offset": "bad"},
            {"limit": 0},
            {"limit": 101},
            {"is_active": "bad"},
            {"location_type": "UNKNOWN"},
            {"parent_location_id": "bad"},
            {"unknown": "value"},
        ]
        with patch.object(
            ListStockLocationsHandler, "execute", new_callable=AsyncMock
        ) as execute:
            for params in invalid:
                with self.subTest(params=params):
                    response = await self.client.get(self.url, params=params)
                    self.assertEqual(response.status_code, 422, response.text)
            execute.assert_not_awaited()
        response = await self.client.get(
            self.url,
            params={"is_active": "false", "location_type": "STORAGE", "search": " A "},
        )
        self.assertEqual(response.status_code, 200, response.text)
        query = self.queries.list.await_args.args[0]
        self.assertIs(query.is_active, False)
        self.assertEqual(
            (query.search, query.location_type), ("A", LocationType.STORAGE)
        )

    async def test_domain_and_storage_errors_have_expected_status(self) -> None:
        """Сохраняет различие отсутствия, конфликта уникальности и ошибки Domain."""
        for payload in (
            {**self.payload, "code": " "},
            {**self.payload, "name": "\u200bName"},
        ):
            response = await self.client.post(
                self.url, headers=self.headers, json=payload
            )
            self.assertEqual(response.status_code, 422, response.text)
        self.locations.add.side_effect = StockLocationCodeAlreadyExistsError("conflict")
        self.assertEqual(
            (
                await self.client.post(
                    self.url, headers=self.headers, json=self.payload
                )
            ).status_code,
            409,
        )
        self.locations.add.side_effect = None
        self.assertEqual(
            (
                await self.client.post(
                    self.url,
                    headers=self.headers,
                    json={**self.payload, "parent_location_id": str(uuid4())},
                )
            ).status_code,
            404,
        )
        self.warehouses.get_for_share.return_value = self.warehouse.deactivate()
        self.assertEqual(
            (
                await self.client.post(
                    self.url, headers=self.headers, json=self.payload
                )
            ).status_code,
            422,
        )
        self.warehouses.get_for_share.return_value = None
        self.assertEqual(
            (
                await self.client.post(
                    self.url, headers=self.headers, json=self.payload
                )
            ).status_code,
            404,
        )
        self.queries.warehouse_exists.return_value = False
        self.assertEqual((await self.client.get(self.url)).status_code, 404)
        self.queries.get_details.return_value = None
        self.assertEqual(
            (await self.client.get(f"{self.url}/{uuid4()}")).status_code, 404
        )

    async def test_auth_tenant_csrf_and_path_uuid_are_enforced(self) -> None:
        """Все методы требуют контекст, POST требует CSRF, UUID проверяет Presentation."""
        self.assertEqual(
            (await self.client.post(self.url, json=self.payload)).status_code, 403
        )
        for principal, expected in (
            (None, 401),
            (replace(self.context.principal, tenant_id=None), 403),
        ):
            self.app.state.test_context = replace(self.context, principal=principal)
            for method, path in (
                ("POST", self.url),
                ("GET", self.url),
                ("GET", f"{self.url}/{self.location_id}"),
            ):
                with self.subTest(method=method, principal=principal):
                    response = await self.client.request(
                        method,
                        path,
                        headers=self.headers,
                        **({"json": self.payload} if method == "POST" else {}),
                    )
                    self.assertEqual(response.status_code, expected, response.text)
        self.app.state.test_context = self.context
        self.assertEqual((await self.client.get(f"{self.url}/bad")).status_code, 422)
        self.assertEqual(
            (
                await self.client.get("/api/console/inventory/warehouses/bad/locations")
            ).status_code,
            422,
        )
        self.warehouses.get_for_share.assert_not_awaited()
        self.queries.list.assert_not_awaited()
