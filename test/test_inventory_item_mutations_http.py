"""Контракты PUT/PATCH/DELETE с реальными handlers, mapper и внешним UoW."""

from dataclasses import replace
from decimal import Decimal, localcontext
from types import SimpleNamespace
from typing import Any
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy.sql.dml import Insert, Update
from sqlalchemy.sql.selectable import Exists, Select
from sqlalchemy.exc import IntegrityError

from src.config import dnk_config
from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.domain.auth.request_context import RequestContext
from src.modules.inventory.application.inventory_item.command.update_inventory_item.handler import (
    UpdateInventoryItemHandler,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)
from src.modules.inventory.infrastructure.persistence.models.item_barcode import (
    ItemBarcodeModel,
)
from test.inventory_item_support import inventory_item_app


class InventoryItemMutationsHttpTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет явные транспортные контракты и завершение общего UoW."""

    async def asyncSetUp(self) -> None:
        """Собирает приложение с сохранённой позицией, штрихкодом и тестовой сессией."""
        self.context = RequestContext(
            Principal(str(uuid4()), str(uuid4()), "session", ("member",)),
            None,
            None,
            None,
        )
        self.row = dict(
            id=uuid4(),
            sku="original",
            base_uom="PCS",
            quantity_step=Decimal("1"),
            tracking_mode="SERIAL",
            expiration_mode="NONE",
        )
        self.barcodes = [
            dict(
                id=uuid4(), inventory_item_id=self.row["id"], barcode="0001", position=0
            )
        ]
        self.failure_on = None
        self.failure = None
        self.session = SimpleNamespace(
            execute=AsyncMock(side_effect=self.execute),
            scalars=AsyncMock(side_effect=self.scalars),
            scalar=AsyncMock(side_effect=self.scalar),
            commit=AsyncMock(),
            rollback=AsyncMock(),
            close=AsyncMock(),
        )
        self.app = inventory_item_app(lambda: self.session, self.context)
        self.app.state.uuid_generator = Mock(new=Mock(side_effect=uuid4))
        scheme = "http" if dnk_config.AUTH.allow_insecure_http else "https"
        self.origin = f"{scheme}://tenant.example"
        self.client = AsyncClient(
            transport=ASGITransport(app=self.app, raise_app_exceptions=False),
            base_url=self.origin,
        )
        token = (await self.client.get("/csrf")).json()["csrf_token"]
        self.headers = {"Origin": self.origin, "X-CSRF-Token": token}
        self.url = f'/api/console/inventory/items/{self.row["id"]}'
        self.put = dict(
            sku="original",
            base_uom="PCS",
            quantity_rules={"step": "1"},
            tracking_mode="SERIAL",
            expiration_mode="NONE",
            barcodes=["0001"],
        )

    async def execute(self, statement: Any, parameters: Any = None) -> Mock:
        """Возвращает независимые SQL-результаты для корня, дочерних строк и записи."""
        if self.failure_on is not None and isinstance(statement, self.failure_on):
            raise self.failure
        result = Mock()
        if isinstance(statement, Select):
            if any(isinstance(column, Exists) for column in statement.selected_columns):
                result.scalar_one.return_value = False
                return result
            table = statement.get_final_froms()[0]
            model = InventoryItemModel(**self.row) if self.row is not None else None
            result.scalars.return_value.one_or_none.return_value = model
            if table.name == "inventory_item_barcodes":
                result.scalars.return_value.all.return_value = [
                    ItemBarcodeModel(**row) for row in self.barcodes
                ]
            elif table.name == "inventory_item_packagings":
                result.scalars.return_value.all.return_value = []
            else:
                result.scalars.return_value.all.return_value = [model]
        else:
            result.scalar_one_or_none.return_value = self.row["id"]
        return result

    async def scalars(self, statement: Any) -> Mock:
        """Возвращает ORM-модели из тестового результата SELECT."""
        result = await self.session.execute(statement)
        return result.scalars()

    async def scalar(self, statement: Any) -> UUID | None:
        """Возвращает ID из RETURNING; запрос использования в Catalog не находит связи."""
        if isinstance(statement, Select):
            return None
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def asyncTearDown(self) -> None:
        """Закрывает HTTP-клиент теста."""
        await self.client.aclose()

    async def test_put_requires_full_body_and_applies_final_configuration(self) -> None:
        """Единица, шаг и режим меняются вместе, ответ содержит новую версию и прежний ID."""
        response = await self.client.put(
            self.url,
            headers=self.headers,
            json={
                **self.put,
                "base_uom": "KG",
                "quantity_rules": {"step": "0.001"},
                "tracking_mode": "LOT",
                "expiration_mode": "REQUIRED",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["base_uom"], "KG")
        self.assertEqual(body["quantity_rules"], {"step": "0.001"})
        self.assertEqual(body["barcodes"][0]["id"], str(self.barcodes[0]["id"]))
        self.session.commit.assert_awaited_once()
        for field in self.put:
            with self.subTest(field=field):
                incomplete = dict(self.put)
                del incomplete[field]
                rejected = await self.client.put(
                    self.url, headers=self.headers, json=incomplete
                )
                self.assertEqual(rejected.status_code, 422, rejected.text)

    async def test_patch_omitted_fields_are_preserved_and_empty_barcodes_clear(
        self,
    ) -> None:
        """PATCH имени не меняет режимы и штрихкоды, явный [] очищает коллекцию."""
        response = await self.client.patch(
            self.url,
            headers=self.headers,
            json={"sku": " Renamed "},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(
            (body["sku"], body["base_uom"], body["tracking_mode"]),
            ("renamed", "PCS", "SERIAL"),
        )
        self.assertEqual(body["barcodes"][0]["barcode"], "0001")
        cleared = await self.client.patch(
            self.url, headers=self.headers, json={"barcodes": []}
        )
        self.assertEqual(cleared.status_code, 200, cleared.text)
        self.assertEqual(cleared.json()["barcodes"], [])

    async def test_identical_put_does_not_update(self) -> None:
        """Повторное идентичное представление не вызывает запись или генерацию UUID."""
        response = await self.client.put(self.url, headers=self.headers, json=self.put)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("version", response.json())
        self.assertNotIn("is_in_use", response.json())
        self.assertTrue(
            all(
                isinstance(call.args[0], Select)
                for call in self.session.execute.await_args_list
            )
        )
        self.app.state.uuid_generator.new.assert_not_called()

    async def test_invalid_patch_and_decimal_values_are_422(self) -> None:
        """Отклоняет null, пустые изменения, неизвестные поля и нестроковый Decimal."""
        invalid = [
            {},
            {"unknown": "value"},
            {"quantity_rules": {}},
            {"barcodes": ["a", " a "]},
        ]
        invalid.extend(
            {field: None}
            for field in (
                "sku",
                "base_uom",
                "quantity_rules",
                "tracking_mode",
                "expiration_mode",
                "barcodes",
            )
        )
        for payload in invalid:
            with self.subTest(payload=payload):
                response = await self.client.patch(
                    self.url, headers=self.headers, json=payload
                )
                self.assertEqual(response.status_code, 422, response.text)
        for method in ("put", "patch"):
            for value in (0.5, "invalid", "NaN", "sNaN", "Infinity", "-Infinity"):
                with (
                    self.subTest(method=method, value=value),
                    localcontext() as context,
                ):
                    context.clear_flags()
                    response = await getattr(self.client, method)(
                        self.url,
                        headers=self.headers,
                        json={**self.put, "quantity_rules": {"step": value}},
                    )
                    self.assertEqual(response.status_code, 422, response.text)
                    self.assertFalse(any(context.flags.values()))

    async def test_request_schema_rejects_invalid_payload_before_handler(self) -> None:
        """Проверяет структуру PUT/PATCH в Presentation без вызова Application."""
        invalid = [
            {"unknown": "value"},
            {"sku": 123},
            {"base_uom": False},
            {"quantity_rules": {}},
            {"quantity_rules": {"step": 1}},
            {"tracking_mode": "unknown"},
            {"expiration_mode": "unknown"},
            {"barcodes": "code"},
            {"barcodes": [123]},
            *({field: None} for field in self.put),
        ]
        with patch.object(
            UpdateInventoryItemHandler, "execute", new_callable=AsyncMock
        ) as execute:
            for method in ("PUT", "PATCH"):
                payloads = [
                    values if method == "PATCH" else {**self.put, **values}
                    for values in invalid
                ]
                payloads.append({})
                if method == "PUT":
                    payloads.extend(
                        {key: value for key, value in self.put.items() if key != field}
                        for field in self.put
                    )
                for payload in payloads:
                    with self.subTest(method=method, payload=payload):
                        response = await self.client.request(
                            method, self.url, headers=self.headers, json=payload
                        )
                        self.assertEqual(response.status_code, 422, response.text)
            execute.assert_not_awaited()
        self.session.execute.assert_not_awaited()

    async def test_missing_items_return_404(self) -> None:
        """Все операции различают отсутствующую позицию и неправильный запрос."""
        self.row = None
        self.assertEqual(
            (
                await self.client.put(self.url, headers=self.headers, json=self.put)
            ).status_code,
            404,
        )
        self.assertEqual(
            (
                await self.client.patch(
                    self.url, headers=self.headers, json={"sku": "new"}
                )
            ).status_code,
            404,
        )
        self.assertEqual(
            (await self.client.delete(self.url, headers=self.headers)).status_code, 404
        )

    async def test_delete_has_no_body_and_no_preconditions(self) -> None:
        """Удаляет существующую позицию по ID и возвращает настоящий пустой 204."""
        response = await self.client.delete(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(response.content, b"")
        self.session.commit.assert_awaited_once()

    async def test_mutations_require_authentication_tenant_and_csrf(self) -> None:
        """Закрывает все три операции без доверенного tenant и CSRF."""
        for principal, expected in (
            (None, 401),
            (replace(self.context.principal, tenant_id=None), 403),
            (self.context.principal, 403),
        ):
            self.app.state.test_context = replace(self.context, principal=principal)
            for method in ("put", "patch", "delete"):
                options = {} if method == "delete" else {"json": self.put}
                response = await self.client.request(
                    method.upper(), self.url, **options
                )
                self.assertEqual(response.status_code, expected, response.text)
        self.session.execute.assert_not_awaited()

    async def test_write_conflicts_rollback_and_commit_failure_is_not_success(
        self,
    ) -> None:
        """Проверяет conflict-путь до rollback и завершение UoW до HTTP-ответа."""
        for statement_type, constraint in (
            (Update, "uq_inventory_items_sku"),
            (Insert, "uq_inventory_item_barcodes_barcode"),
        ):
            original = RuntimeError("unique")
            original.sqlstate = "23505"
            original.constraint_name = constraint
            self.failure_on = statement_type
            self.failure = IntegrityError("write", {}, original)
            self.session.rollback.reset_mock()
            response = await self.client.patch(
                self.url,
                headers=self.headers,
                json={"sku": "new"},
            )
            self.assertEqual(response.status_code, 409, response.text)
            self.session.rollback.assert_awaited_once()
        self.failure_on = None
        self.session.commit.side_effect = RuntimeError("commit failed")
        with self.assertLogs(
            "src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy",
            level="ERROR",
        ):
            response = await self.client.delete(self.url, headers=self.headers)
        self.assertEqual(response.status_code, 500)
