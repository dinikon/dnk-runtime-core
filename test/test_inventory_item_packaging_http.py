"""HTTP-контракты дочерних упаковок с настоящими схемами, handlers, auth и CSRF."""

from dataclasses import replace
from decimal import Decimal
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from httpx import ASGITransport, AsyncClient
from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.inventory.application.inventory_item.command.add_item_packaging.handler import (
    AddItemPackagingHandler,
)
from src.modules.inventory.application.inventory_item.query.get_item_packaging.dto import (
    GetItemPackagingResultDTO,
)
from src.modules.inventory.application.inventory_item.query.list_item_packagings.dto import (
    ListItemPackagingsResultDTO,
    ItemPackagingListItemDTO,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemConflictError
from src.modules.inventory.presentation.inventory_item.depends import (
    get_inventory_item_repository,
    get_item_packaging_query_repository,
)
from src.modules.inventory.presentation.packaging_type.depends import (
    get_packaging_type_repository,
)
from test.inventory_item_support import inventory_item_app
from test import test_inventory_item_packaging_application as application_support


class ItemPackagingHttpTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет явную границу валидации и независимые response-контракты."""

    async def asyncSetUp(self) -> None:
        """Собирает реальные HTTP endpoints с изолированными портами."""
        fixture = application_support.ItemPackagingApplicationTests()
        fixture.setUp()
        self.item, self.kind, self.items, self.types = (
            fixture.item,
            fixture.kind,
            fixture.items,
            fixture.types,
        )
        self.identifier = uuid4()
        self.context = RequestContext(
            Principal(str(uuid4()), str(uuid4()), "session", ("member",)),
            None,
            None,
            None,
        )
        self.app = inventory_item_app(Mock(), self.context)
        self.app.state.uuid_generator = Mock(new=Mock(return_value=self.identifier))
        self.app.dependency_overrides[get_inventory_item_repository] = (
            lambda: self.items
        )
        self.app.dependency_overrides[get_packaging_type_repository] = (
            lambda: self.types
        )
        values = (
            self.identifier,
            self.item.id.uuid,
            self.kind.id.uuid,
            "BOX-12",
            "Ящик",
            Decimal("12"),
            "PCS",
        )
        self.queries = Mock(
            item_exists=AsyncMock(return_value=True),
            get_details=AsyncMock(return_value=GetItemPackagingResultDTO(*values)),
            list=AsyncMock(
                return_value=ListItemPackagingsResultDTO(
                    (ItemPackagingListItemDTO(*values),), 1, 0, 50
                )
            ),
        )
        self.app.dependency_overrides[get_item_packaging_query_repository] = (
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
        self.url = f"/api/console/inventory/items/{self.item.id.uuid}/packagings"
        self.payload = {
            "packaging_type_id": str(self.kind.id.uuid),
            "code": " BOX-12 ",
            "name": " Ящик ",
            "content_quantity": "12",
            "content_uom": "PCS",
        }

    async def test_create_list_card_and_openapi_contracts(self) -> None:
        """Сохраняет регистр, server UUID, owner и Decimal-строку, разделяет ответы методов."""
        response = await self.client.post(
            self.url, headers=self.headers, json=self.payload
        )
        self.assertEqual(response.status_code, 201, response.text)
        expected = {
            "id": str(self.identifier),
            "inventory_item_id": str(self.item.id.uuid),
            "packaging_type_id": str(self.kind.id.uuid),
            "code": "BOX-12",
            "name": "Ящик",
            "content_quantity": "12",
            "content_uom": "PCS",
        }
        self.assertEqual(response.json(), expected)
        self.assertEqual(
            (await self.client.get(f"{self.url}/{self.identifier}")).json(), expected
        )
        self.assertEqual(
            (await self.client.get(self.url)).json(),
            {"items": [expected], "total": 1, "offset": 0, "limit": 50},
        )
        schemas = self.app.openapi()["components"]["schemas"]
        for name in (
            "AddItemPackagingResponse",
            "GetItemPackagingResponse",
            "ListItemPackagingsResponse",
        ):
            self.assertIn(name, schemas)
        request = schemas["AddItemPackagingRequest"]
        self.assertEqual(request["properties"]["content_quantity"]["type"], "string")

    async def test_structure_is_checked_before_handler(self) -> None:
        """Отклоняет неполноту, null, ручной ID, JSON-числа и нечисловые строки."""
        invalid = [
            {},
            *(
                {k: v for k, v in self.payload.items() if k != field}
                for field in self.payload
            ),
            *({**self.payload, field: None} for field in self.payload),
            *(
                {**self.payload, "content_quantity": v}
                for v in [1, 1.5, True, "NaN", "Infinity", "-Infinity", "bad"]
            ),
            *(
                {**self.payload, field: value}
                for field, value in [
                    ("code", 1),
                    ("name", False),
                    ("content_uom", 1),
                    ("packaging_type_id", "bad"),
                    ("id", str(uuid4())),
                    ("inventory_item_id", str(uuid4())),
                    ("is_active", False),
                    ("unknown", 1),
                ]
            ),
        ]
        with patch.object(
            AddItemPackagingHandler, "execute", new_callable=AsyncMock
        ) as execute:
            for payload in invalid:
                with self.subTest(payload=payload):
                    response = await self.client.post(
                        self.url, headers=self.headers, json=payload
                    )
                    self.assertEqual(response.status_code, 422, response.text)
            execute.assert_not_awaited()
        self.items.save.assert_not_awaited()

    async def test_domain_errors_and_missing_resources(self) -> None:
        """Domain отвечает за положительность, совместимость и конфликт назначения."""
        for changes in (
            {"content_quantity": "0"},
            {"content_quantity": "-1"},
            {"content_quantity": "0.5"},
            {"content_uom": "KG"},
            {"content_uom": "UNKNOWN"},
            {"code": " "},
            {"name": "\u200bName"},
        ):
            response = await self.client.post(
                self.url, headers=self.headers, json={**self.payload, **changes}
            )
            self.assertEqual(response.status_code, 422, response.text)
        self.types.get_for_update.return_value = self.kind.deactivate()
        self.assertEqual(
            (
                await self.client.post(
                    self.url, headers=self.headers, json=self.payload
                )
            ).status_code,
            409,
        )
        self.types.get_for_update.return_value = None
        self.assertEqual(
            (
                await self.client.post(
                    self.url, headers=self.headers, json=self.payload
                )
            ).status_code,
            404,
        )
        self.types.get_for_update.return_value = self.kind
        self.items.save.side_effect = InventoryItemConflictError("code conflict")
        self.assertEqual(
            (
                await self.client.post(
                    self.url, headers=self.headers, json=self.payload
                )
            ).status_code,
            409,
        )
        self.items.get_for_update.return_value = None
        self.assertEqual(
            (
                await self.client.post(
                    self.url, headers=self.headers, json=self.payload
                )
            ).status_code,
            404,
        )
        self.queries.item_exists.return_value = False
        self.assertEqual((await self.client.get(self.url)).status_code, 404)
        self.queries.get_details.return_value = None
        self.assertEqual(
            (await self.client.get(f"{self.url}/{uuid4()}")).status_code, 404
        )

    async def test_list_validation_and_search_normalization(self) -> None:
        """Проверяет границы пагинации, неизвестные query-поля и пробелы поиска."""
        for params in (
            {"offset": -1},
            {"offset": 2147483648},
            {"limit": 0},
            {"limit": 101},
            {"limit": "bad"},
            {"unknown": "x"},
        ):
            response = await self.client.get(self.url, params=params)
            self.assertEqual(response.status_code, 422, response.text)
        response = await self.client.get(
            self.url, params={"search": " BOX ", "offset": 20, "limit": 20}
        )
        self.assertEqual(response.status_code, 200, response.text)
        query = self.queries.list.await_args.args[0]
        self.assertEqual(
            (query.inventory_item_id, query.search, query.offset, query.limit),
            (self.item.id, "BOX", 20, 20),
        )

    async def test_auth_tenant_csrf_and_path_uuid(self) -> None:
        """Чтение требует контекст, запись требует CSRF, оба path UUID проверяются."""
        self.assertEqual(
            (await self.client.post(self.url, json=self.payload)).status_code, 403
        )
        for principal, status in (
            (None, 401),
            (replace(self.context.principal, tenant_id=None), 403),
        ):
            self.app.state.test_context = replace(self.context, principal=principal)
            for method, path in [
                ("POST", self.url),
                ("GET", self.url),
                ("GET", f"{self.url}/{self.identifier}"),
            ]:
                response = await self.client.request(
                    method,
                    path,
                    headers=self.headers,
                    **({"json": self.payload} if method == "POST" else {}),
                )
                self.assertEqual(response.status_code, status, response.text)
        self.app.state.test_context = self.context
        for path in (f"{self.url}/bad", "/api/console/inventory/items/bad/packagings"):
            self.assertEqual((await self.client.get(path)).status_code, 422)
        self.items.get_for_update.assert_not_awaited()
