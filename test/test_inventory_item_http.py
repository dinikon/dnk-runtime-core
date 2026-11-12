"""HTTP-контракты создания и списка, защита и границы внешнего UoW."""

from dataclasses import replace
from decimal import Decimal, InvalidOperation, localcontext
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.inventory.presentation.inventory_item.http.request.create_inventory_item import (
    CreateInventoryItemQuantityRulesRequest,
)
from test.inventory_item_support import inventory_item_app


class InventoryItemHttpTests(unittest.IsolatedAsyncioTestCase):
    """Использует настоящие handlers и адаптеры с тестовой SQL-сессией."""

    async def asyncSetUp(self) -> None:
        """Собирает HTTP-приложение и получает настоящий CSRF-токен."""
        self.context = RequestContext(
            Principal(str(uuid4()), str(uuid4()), "session", ("member",)),
            None,
            None,
            None,
        )
        self.row = dict(
            id=uuid4(),
            sku="item-1",
            base_uom="KG",
            quantity_step=Decimal("0.001"),
            tracking_mode="LOT",
            expiration_mode="REQUIRED",
        )
        self.result = Mock()
        self.result.mappings.return_value.all.return_value = [self.row]
        self.result.scalar_one.return_value = 1
        self.session = SimpleNamespace(
            execute=AsyncMock(return_value=self.result),
            commit=AsyncMock(),
            rollback=AsyncMock(),
            close=AsyncMock(),
        )
        self.app = inventory_item_app(lambda: self.session, self.context)
        self.app.state.uuid_generator = Mock(new=uuid4)
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}
        self.url = "/api/console/inventory/items"
        self.payload = {
            "sku": " Item-1 ",
            "base_uom": "KG",
            "quantity_rules": {"step": "0.001"},
        }

    async def asyncTearDown(self) -> None:
        """Закрывает HTTP-клиент теста."""
        await self.client.aclose()

    async def test_create_returns_canonical_values_and_barcode_ids(self) -> None:
        """Проверяет контракт POST и единственный commit внешнего UoW."""
        response = await self.client.post(
            self.url,
            headers=self.headers,
            json={**self.payload, "barcodes": ["000AbC", "000abc"]},
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["sku"], "item-1")
        self.assertEqual(body["quantity_rules"], {"step": "0.001"})
        self.assertEqual(body["tracking_mode"], "NONE")
        self.assertEqual(body["expiration_mode"], "NONE")
        self.assertEqual(
            [barcode["barcode"] for barcode in body["barcodes"]], ["000AbC", "000abc"]
        )
        self.assertEqual(
            len({body["id"], *(barcode["id"] for barcode in body["barcodes"])}), 3
        )
        self.session.commit.assert_awaited_once()
        self.session.rollback.assert_not_awaited()
        self.session.close.assert_awaited_once()

    async def test_list_returns_projection_and_empty_page(self) -> None:
        """Проверяет конкретный response списка с точным шагом и метаданными."""
        response = await self.client.get(
            self.url, params={"offset": 2, "limit": 3, "search": " ITEM "}
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual((body["total"], body["offset"], body["limit"]), (1, 2, 3))
        self.assertEqual(body["items"][0]["quantity_rules"], {"step": "0.001"})
        self.assertNotIn("barcodes", body["items"][0])
        self.result.mappings.return_value.all.return_value = []
        self.result.scalar_one.return_value = 0
        empty = (await self.client.get(self.url)).json()
        self.assertEqual(empty, {"items": [], "total": 0, "offset": 0, "limit": 50})

    async def test_create_only_sku_and_partial_settings_use_domain_defaults(
        self,
    ) -> None:
        """POST принимает только SKU; явно переданные настройки не подменяются defaults."""
        for settings, expected in (
            ({}, ("PCS", "1", "NONE", "NONE")),
            ({"base_uom": "KG"}, ("KG", "1", "NONE", "NONE")),
            (
                {"quantity_rules": {"step": "0.000000000000000000001"}},
                ("PCS", "1E-21", "NONE", "NONE"),
            ),
            (
                {"tracking_mode": "SERIAL", "expiration_mode": "REQUIRED"},
                ("PCS", "1", "SERIAL", "REQUIRED"),
            ),
            ({"expiration_mode": "OPTIONAL"}, ("PCS", "1", "NONE", "OPTIONAL")),
        ):
            with self.subTest(settings=settings):
                response = await self.client.post(
                    self.url,
                    headers=self.headers,
                    json={"sku": " Default ", **settings},
                )
                self.assertEqual(response.status_code, 201, response.text)
                value = response.json()
                self.assertEqual(value["sku"], "default")
                self.assertEqual(
                    (
                        value["base_uom"],
                        value["quantity_rules"]["step"],
                        value["tracking_mode"],
                        value["expiration_mode"],
                    ),
                    expected,
                )
                self.assertEqual(value["barcodes"], [])

    async def test_creation_absence_differs_from_null_empty_and_invalid_values(
        self,
    ) -> None:
        """Проверяет обязательность ручного SKU и запрет скрытой подстановки defaults."""
        invalid = [{}, {"sku": None}, {"sku": ""}]
        for field in (
            "base_uom",
            "quantity_rules",
            "tracking_mode",
            "expiration_mode",
            "barcodes",
        ):
            invalid.append({"sku": "manual", field: None})
        invalid.extend(
            [
                {"sku": "manual", "base_uom": ""},
                {"sku": "manual", "quantity_rules": {}},
                {"sku": "manual", "quantity_rules": {"step": "0"}},
                {"sku": "manual", "quantity_rules": {"step": 1}},
                {"sku": "manual", "expiration_mode": "REQUIRED"},
                {"sku": "manual", "base_uom": "KG", "tracking_mode": "SERIAL"},
            ]
        )
        for payload in invalid:
            with self.subTest(payload=payload):
                response = await self.client.post(
                    self.url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, 422, response.text)
        self.session.execute.assert_not_awaited()

    async def test_detail_projection_exact_decimal_ordered_barcodes_and_missing(
        self,
    ) -> None:
        """Проверяет чтение карточки без write-репозитория и HTTP 404."""
        barcode_id = uuid4()
        step = "0.123456789012345678901234567890123456789"
        self.result.mappings.return_value.all.return_value = [
            {
                **self.row,
                "quantity_step": Decimal(step),
                "barcode_id": barcode_id,
                "barcode": "000AbC",
            }
        ]
        response = await self.client.get(f"{self.url}/{self.row['id']}")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["quantity_rules"], {"step": step})
        self.assertEqual(
            body["barcodes"], [{"id": str(barcode_id), "barcode": "000AbC"}]
        )
        self.assertEqual(body["id"], str(self.row["id"]))
        self.result.mappings.return_value.all.return_value = [
            {**self.row, "barcode_id": None, "barcode": None}
        ]
        self.assertEqual(
            (await self.client.get(f"{self.url}/{self.row['id']}")).json()["barcodes"],
            [],
        )
        self.result.mappings.return_value.all.return_value = []
        self.assertEqual(
            (await self.client.get(f"{self.url}/{uuid4()}")).status_code, 404
        )
        self.assertEqual(
            (await self.client.get(f"{self.url}/invalid-id")).status_code, 422
        )

    async def test_uoms_are_domain_dictionary_and_do_not_open_storage(self) -> None:
        """Публикует все Domain-единицы, включая неканонические базовые коды."""
        from src.modules.inventory.domain.uom_catalog import list_uoms

        response = await self.client.get("/api/console/inventory/uoms")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {
                "items": [
                    {"code": unit.code.value, "dimension": unit.dimension.value}
                    for unit in list_uoms()
                ]
            },
        )
        self.session.execute.assert_not_awaited()
        self.session.commit.assert_not_awaited()

    async def test_read_endpoints_require_authentication_and_tenant(self) -> None:
        """Не раскрывает карточку и справочник вне контекста пользователя и tenant."""
        for principal, expected in (
            (None, 401),
            (replace(self.context.principal, tenant_id=None), 403),
        ):
            self.app.state.test_context = replace(self.context, principal=principal)
            for url in (f"{self.url}/{uuid4()}", "/api/console/inventory/uoms"):
                self.assertEqual((await self.client.get(url)).status_code, expected)
        self.session.execute.assert_not_awaited()

    async def test_invalid_payloads_and_query_parameters_never_write(self) -> None:
        """Отклоняет неправильные значения и несовместимые настройки до SQL."""
        for changes in (
            {"sku": " "},
            {"sku": 123},
            {"sku": "ß" * 13},
            {"base_uom": "kg"},
            {"quantity_rules": {}},
            {"quantity_rules": {"step": 0.001}},
            {"quantity_rules": {"step": "0"}},
            {"quantity_rules": {"step": "NaN"}},
            {"quantity_rules": {"step": "Infinity"}},
            {"quantity_rules": {"step": "invalid"}},
            {"quantity_rules": {"step": "1", "scale": 1}},
            {"tracking_mode": "SERIAL"},
            {"expiration_mode": "REQUIRED"},
            {"tracking_mode": "invalid"},
            {"barcodes": [123]},
            {"barcodes": ["0001", " 0001 "]},
            {"packagings": []},
            {"id": str(uuid4())},
        ):
            with self.subTest(changes=changes):
                response = await self.client.post(
                    self.url, headers=self.headers, json={**self.payload, **changes}
                )
                self.assertEqual(response.status_code, 422, response.text)
        for params in ({"offset": -1}, {"limit": 0}, {"limit": 101}, {"limit": "x"}):
            with self.subTest(params=params):
                self.assertEqual(
                    (await self.client.get(self.url, params=params)).status_code, 422
                )
        self.session.execute.assert_not_awaited()

    async def test_sku_length_is_checked_after_domain_normalization(self) -> None:
        """Не ограничивает исходную строку до trim и casefold в Domain."""
        response = await self.client.post(
            self.url,
            headers=self.headers,
            json={**self.payload, "sku": " " * 40 + "A" * 25 + " " * 40},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["sku"], "a" * 25)

    async def test_step_validation_preserves_caller_decimal_context(self) -> None:
        """Не меняет Decimal-флаги вызывающего кода на ошибочном или точном вводе."""
        with localcontext() as context:
            context.prec = 2
            for trap in (False, True):
                context.traps[InvalidOperation] = trap
                context.clear_flags()
                for value in ("invalid", "NaN", "sNaN", "Infinity", "-Infinity"):
                    with self.subTest(value=value, trap=trap):
                        with self.assertRaises(ValidationError):
                            CreateInventoryItemQuantityRulesRequest(step=value)
                        self.assertFalse(any(context.flags.values()))
                value = "0.12345678901234567890123456789"
                request = CreateInventoryItemQuantityRulesRequest(step=value)
                self.assertEqual(request.step, Decimal(value))
                self.assertFalse(any(context.flags.values()))

    async def test_known_unique_conflicts_return_409_and_rollback(self) -> None:
        """Проверяет путь от драйверного unique-конфликта до HTTP и rollback."""
        for constraint in (
            "uq_inventory_items_sku",
            "uq_inventory_item_barcodes_barcode",
        ):
            with self.subTest(constraint=constraint):
                driver = RuntimeError("unique")
                driver.constraint_name = constraint
                original = RuntimeError("wrapper")
                original.sqlstate = "23505"
                original.__cause__ = driver
                self.session.execute.side_effect = IntegrityError(
                    "insert", {}, original
                )
                self.session.rollback.reset_mock()
                response = await self.client.post(
                    self.url, headers=self.headers, json=self.payload
                )
                self.assertEqual(response.status_code, 409, response.text)
                self.session.rollback.assert_awaited_once()
        self.session.commit.assert_not_awaited()

    async def test_authentication_tenant_and_csrf_are_required(self) -> None:
        """Закрывает оба метода без principal/tenant и создание без CSRF."""
        self.app.state.test_context = replace(self.context, principal=None)
        self.assertEqual((await self.client.get(self.url)).status_code, 401)
        self.assertEqual(
            (await self.client.post(self.url, json=self.payload)).status_code, 401
        )
        self.app.state.test_context = replace(
            self.context, principal=replace(self.context.principal, tenant_id=None)
        )
        self.assertEqual((await self.client.get(self.url)).status_code, 403)
        self.assertEqual(
            (
                await self.client.post(
                    self.url, headers=self.headers, json=self.payload
                )
            ).status_code,
            403,
        )
        self.app.state.test_context = self.context
        self.assertEqual(
            (await self.client.post(self.url, json=self.payload)).status_code, 403
        )
        self.session.execute.assert_not_awaited()

    async def test_storage_and_commit_failures_do_not_return_success(self) -> None:
        """Передаёт технический отказ наружу и завершает UoW с rollback."""
        self.session.execute.side_effect = RuntimeError("storage unavailable")
        self.assertEqual((await self.client.get(self.url)).status_code, 500)
        self.session.rollback.assert_awaited_once()
        self.session.execute.side_effect = None
        self.session.rollback.reset_mock()
        self.session.commit.side_effect = RuntimeError("commit failed")
        with self.assertLogs(
            "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
            level="ERROR",
        ):
            response = await self.client.post(
                self.url, headers=self.headers, json=self.payload
            )
        self.assertEqual(response.status_code, 500)
        self.session.rollback.assert_awaited_once()
