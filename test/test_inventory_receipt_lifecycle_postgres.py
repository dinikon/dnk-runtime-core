"""Жизненный цикл поступлений: реальные блокировки, версии, строки и HTTP на PostgreSQL."""

import asyncio
import os
import unittest
from unittest.mock import patch
from uuid import uuid4
from src.modules.inventory.infrastructure.stock_document.persistence.repository import (
    SqlAlchemyStockDocumentRepository,
)
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from test import test_inventory_receipt_postgres as support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class ReceiptLifecyclePostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет новые команды через реальный общий UoW и проекции карточки."""

    drop_schemas = support.InventoryReceiptPostgresTests.drop_schemas
    create_receipt = support.InventoryReceiptPostgresTests.create_receipt

    async def asyncSetUp(self) -> None:
        """Создаёт изолированные tenant, компанию, склад и SKU первого среза."""
        await support.InventoryReceiptPostgresTests.asyncSetUp(self)

    def existing_lines(self, document: dict) -> list[dict]:
        """Восстанавливает исходный ввод для атомарного сохранения существующих строк."""
        return [
            dict(
                id=line["id"], quantity=line["source_quantity"], uom=line["source_uom"]
            )
            for line in document["lines"]
        ]

    async def test_edit_removes_changes_adds_and_retains_identity(self) -> None:
        """Сохраняет ID, исторический SKU, точный пересчёт и плотный порядок после удаления."""
        original = await self.create_receipt()
        url = f"{self.receipts}/{original['id']}"
        await self.client.patch(
            f"/api/console/inventory/items/{self.item['id']}",
            headers=self.headers,
            json={"sku": "renamed"},
        )
        lines = [
            dict(id=original["lines"][1]["id"], quantity="2000", uom="G"),
            dict(
                inventory_item_id=self.item["id"],
                quantity="1234567890.1234567890123456789",
                uom="KG",
            ),
        ]
        response = await self.client.patch(
            url, headers=self.headers, json={"expected_version": 2, "lines": lines}
        )
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["version"], 5)
        self.assertEqual([l["position"] for l in result["lines"]], [0, 1])
        self.assertEqual(result["lines"][0]["id"], original["lines"][1]["id"])
        self.assertEqual([l["sku"] for l in result["lines"]], ["oil-001", "renamed"])
        self.assertEqual(result["lines"][0]["planned_qty"], "2.000")
        self.assertEqual(
            result["lines"][1]["planned_qty"], "1234567890.1234567890123456789"
        )
        self.assertEqual((await self.client.get(url)).json(), result)

    async def test_noop_and_empty_draft(self) -> None:
        """Не увеличивает версию прежнего ввода; удаление всех строк возвращает пустой DRAFT."""
        original = await self.create_receipt()
        url = f"{self.receipts}/{original['id']}"
        response = await self.client.patch(
            url,
            headers=self.headers,
            json={"expected_version": 2, "lines": self.existing_lines(original)},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), original)
        response = await self.client.patch(
            url, headers=self.headers, json={"expected_version": 2, "lines": []}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            (response.json()["version"], response.json()["lines"]), (4, [])
        )
        self.assertEqual(
            (
                await self.client.post(
                    url + "/confirm", headers=self.headers, json={"expected_version": 4}
                )
            ).status_code,
            422,
        )
        self.assertEqual(
            (
                await self.client.post(
                    url + "/cancel", headers=self.headers, json={"expected_version": 4}
                )
            ).status_code,
            200,
        )
        self.assertEqual(
            (
                await self.client.patch(
                    url, headers=self.headers, json={"expected_version": 5, "lines": []}
                )
            ).status_code,
            409,
        )

    async def test_confirm_freezes_plan_cancel_retains_references_and_creation_replay(
        self,
    ) -> None:
        """Подтверждение фиксирует план; отмена не удаляет его и не переписывает исходный ответ создания."""
        key = str(uuid4())
        original = await self.create_receipt(key=key)
        url = f"{self.receipts}/{original['id']}"
        response = await self.client.post(
            url + "/confirm", headers=self.headers, json={"expected_version": 2}
        )
        self.assertEqual(response.status_code, 200, response.text)
        confirmed = response.json()
        self.assertEqual((confirmed["version"], confirmed["status"]), (3, "CONFIRMED"))
        self.assertEqual(confirmed["lines"], original["lines"])
        self.assertEqual(await self.create_receipt(key=key), original)
        self.assertEqual((await self.client.get(url)).json(), confirmed)
        for path, payload in [
            (url, {"expected_version": 3, "lines": self.existing_lines(original)}),
            (url + "/confirm", {"expected_version": 3}),
        ]:
            response = await (
                self.client.patch(path, headers=self.headers, json=payload)
                if path == url
                else self.client.post(path, headers=self.headers, json=payload)
            )
            self.assertEqual(response.status_code, 409, response.text)
        await self.client.patch(
            f"/api/console/inventory/warehouses/{self.warehouse['id']}",
            headers=self.headers,
            json={"is_active": False},
        )
        response = await self.client.post(
            url + "/cancel", headers=self.headers, json={"expected_version": 3}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            (response.json()["version"], response.json()["status"]), (4, "CANCELLED")
        )
        self.assertEqual(response.json()["lines"], original["lines"])
        for path in [
            f"/api/console/inventory/items/{self.item['id']}",
            f"/api/console/crm/companies/{self.company['id']}",
        ]:
            self.assertEqual(
                (await self.client.delete(path, headers=self.headers)).status_code, 409
            )

    async def test_stale_version_and_unsafe_shape_leave_document_unchanged(
        self,
    ) -> None:
        """Отклоняет устаревшую версию, чужие строки, повтор ID и подмену серверных полей."""
        original = await self.create_receipt()
        other = await self.create_receipt()
        url = f"{self.receipts}/{original['id']}"
        rows = self.existing_lines(original)
        for suffix in ["", "/confirm", "/cancel"]:
            payload = {"expected_version": 1, **({"lines": rows} if not suffix else {})}
            response = await (
                self.client.patch(url, headers=self.headers, json=payload)
                if not suffix
                else self.client.post(url + suffix, headers=self.headers, json=payload)
            )
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(
                response.json()["detail"],
                {
                    "code": "stock_document_version_conflict",
                    "message": "Документ изменён. Загрузите актуальный план перед повторным действием.",
                    "expected_version": 1,
                    "actual_version": 2,
                },
            )
        invalid = [
            {},
            {"expected_version": True, "lines": rows},
            {"expected_version": 2, "lines": rows, "status": "CONFIRMED"},
            {"expected_version": 2, "lines": [rows[0], rows[0]]},
            {
                "expected_version": 2,
                "lines": [{**rows[0], "inventory_item_id": self.item["id"]}],
            },
            {"expected_version": 2, "lines": [{**rows[0], "quantity": 1}]},
        ]
        for payload in invalid:
            self.assertEqual(
                (
                    await self.client.patch(url, headers=self.headers, json=payload)
                ).status_code,
                422,
            )
        response = await self.client.patch(
            url,
            headers=self.headers,
            json={"expected_version": 2, "lines": self.existing_lines(other)},
        )
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual((await self.client.get(url)).json(), original)

    async def test_current_warehouse_and_item_settings_are_checked(self) -> None:
        """Подтверждение отвергает деактивацию и изменение единицы, но отмена остаётся доступной."""
        original = await self.create_receipt()
        url = f"{self.receipts}/{original['id']}"
        wh = f"/api/console/inventory/warehouses/{self.warehouse['id']}"
        await self.client.patch(wh, headers=self.headers, json={"is_active": False})
        self.assertEqual(
            (
                await self.client.post(
                    url + "/confirm", headers=self.headers, json={"expected_version": 2}
                )
            ).status_code,
            422,
        )
        await self.client.patch(wh, headers=self.headers, json={"is_active": True})
        await self.client.patch(
            f"/api/console/inventory/items/{self.item['id']}",
            headers=self.headers,
            json={"base_uom": "L"},
        )
        self.assertEqual(
            (
                await self.client.post(
                    url + "/confirm", headers=self.headers, json={"expected_version": 2}
                )
            ).status_code,
            422,
        )
        self.assertEqual(
            (
                await self.client.post(
                    url + "/cancel", headers=self.headers, json={"expected_version": 2}
                )
            ).status_code,
            200,
        )

    async def test_domain_line_error_has_position_and_no_partial_save(self) -> None:
        """Вторая неверная строка не сохраняет даже корректное изменение первой."""
        original = await self.create_receipt()
        url = f"{self.receipts}/{original['id']}"
        lines = self.existing_lines(original)
        lines[0]["quantity"] = "3000"
        lines[1]["quantity"] = "0"
        response = await self.client.patch(
            url, headers=self.headers, json={"expected_version": 2, "lines": lines}
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["detail"][0]["loc"], ["body", "lines", 1])
        self.assertEqual((await self.client.get(url)).json(), original)

    async def test_storage_failure_rolls_back_root_and_children(self) -> None:
        """Технический отказ после записи откатывает версию и разницу дочернего состава."""
        original = await self.create_receipt()
        url = f"{self.receipts}/{original['id']}"
        save = SqlAlchemyStockDocumentRepository.save

        async def failed(
            repository: SqlAlchemyStockDocumentRepository,
            document: StockDocument,
            *,
            expected_version: int,
        ) -> None:
            """Эмулирует сбой после всех DML до общего commit."""
            await save(repository, document, expected_version=expected_version)
            raise RuntimeError("storage failed")

        with patch.object(SqlAlchemyStockDocumentRepository, "save", failed):
            response = await self.client.patch(
                url,
                headers=self.headers,
                json={
                    "expected_version": 2,
                    "lines": [
                        dict(inventory_item_id=self.item["id"], quantity="1", uom="KG")
                    ],
                },
            )
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual((await self.client.get(url)).json(), original)

    async def test_concurrent_edit_and_confirmation_have_one_winner(self) -> None:
        """Одинаковая ожидаемая версия не позволяет подтвердить чужой изменённый план."""
        original = await self.create_receipt()
        url = f"{self.receipts}/{original['id']}"
        lines = self.existing_lines(original)
        lines[0]["quantity"] = "3000"
        responses = await asyncio.gather(
            self.client.patch(
                url, headers=self.headers, json={"expected_version": 2, "lines": lines}
            ),
            self.client.post(
                url + "/confirm", headers=self.headers, json={"expected_version": 2}
            ),
        )
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [200, 409],
            [r.text for r in responses],
        )
        current = (await self.client.get(url)).json()
        self.assertEqual(current["version"], 3)
        self.assertTrue(all(l["executed_qty"] == "0" for l in current["lines"]))

    async def test_auth_csrf_missing_document_and_tenant_isolation(self) -> None:
        """Новые действия сохраняют существующие границы доступа и tenant-чтения."""
        original = await self.create_receipt()
        url = f"{self.receipts}/{original['id']}"
        self.assertEqual(
            (
                await self.client.post(url + "/confirm", json={"expected_version": 2})
            ).status_code,
            403,
        )
        self.assertEqual(
            (
                await self.client.post(
                    f"{self.receipts}/{uuid4()}/cancel",
                    headers=self.headers,
                    json={"expected_version": 0},
                )
            ).status_code,
            404,
        )

        from dataclasses import replace

        initial = self.app.state.test_context
        self.app.state.test_context = replace(
            initial, principal=replace(initial.principal, tenant_id=str(self.other))
        )
        try:
            for suffix in ("/confirm", "/cancel"):
                response = await self.client.post(
                    url + suffix, headers=self.headers, json={"expected_version": 2}
                )
                self.assertEqual(response.status_code, 404, response.text)
            response = await self.client.patch(
                url,
                headers=self.headers,
                json={"expected_version": 2, "lines": self.existing_lines(original)},
            )
            self.assertEqual(response.status_code, 404, response.text)
        finally:
            self.app.state.test_context = initial

    async def test_partial_execution_blocks_simple_cancellation(self) -> None:
        """Сохранённый частичный факт нельзя отменить простым переходом статуса."""
        from decimal import Decimal
        from uuid import UUID
        from sqlalchemy import update
        from src.modules.inventory.infrastructure.persistence.models.stock_document import (
            StockDocumentModel,
        )
        from src.modules.inventory.infrastructure.persistence.models.stock_document_line import (
            StockDocumentLineModel,
        )
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
            bind_tenant_schema,
        )

        original = await self.create_receipt()
        url = f"{self.receipts}/{original['id']}"
        async with self.engine.begin() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            await connection.execute(
                update(StockDocumentLineModel)
                .where(StockDocumentLineModel.id == UUID(original["lines"][0]["id"]))
                .values(executed_qty=Decimal("1"))
            )
            await connection.execute(
                update(StockDocumentModel)
                .where(StockDocumentModel.id == UUID(original["id"]))
                .values(status="PARTIALLY_EXECUTED", version=3)
            )
        response = await self.client.post(
            url + "/cancel", headers=self.headers, json={"expected_version": 3}
        )
        self.assertEqual(response.status_code, 409, response.text)
        current = (await self.client.get(url)).json()
        self.assertEqual(
            (current["status"], current["version"]), ("PARTIALLY_EXECUTED", 3)
        )
        self.assertEqual(current["lines"][0]["executed_qty"], "1")

    async def test_concurrent_confirm_and_cancel_require_new_version_for_second_action(
        self,
    ) -> None:
        """Отмена не может незаметно сменить статус только что подтверждённого плана."""
        original = await self.create_receipt()
        url = f"{self.receipts}/{original['id']}"
        responses = await asyncio.gather(
            self.client.post(
                url + "/confirm", headers=self.headers, json={"expected_version": 2}
            ),
            self.client.post(
                url + "/cancel", headers=self.headers, json={"expected_version": 2}
            ),
        )
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [200, 409],
            [r.text for r in responses],
        )
        self.assertEqual((await self.client.get(url)).json()["version"], 3)

    async def test_confirmation_holds_current_warehouse_until_commit(self) -> None:
        """Конкурентная деактивация ждёт подтверждения по заблокированному актуальному снимку."""
        from src.modules.inventory.infrastructure.warehouse.persistence.repository import (
            SqlAlchemyWarehouseRepository,
        )
        from src.modules.inventory.domain.warehouse.aggregate import Warehouse
        from src.modules.inventory.domain.warehouse.value_object.identifier import (
            WarehouseIdVO,
        )

        entered, release = asyncio.Event(), asyncio.Event()
        original = await self.create_receipt()
        url = f"{self.receipts}/{original['id']}"
        read = SqlAlchemyWarehouseRepository.get_for_share

        async def held(
            repository: SqlAlchemyWarehouseRepository, identifier: WarehouseIdVO
        ) -> Warehouse | None:
            """Удерживает реально прочитанный склад до запуска изменения активности."""
            warehouse = await read(repository, identifier)
            entered.set()
            await release.wait()
            return warehouse

        with patch.object(SqlAlchemyWarehouseRepository, "get_for_share", held):
            confirmation = asyncio.create_task(
                self.client.post(
                    url + "/confirm", headers=self.headers, json={"expected_version": 2}
                )
            )
            await asyncio.wait_for(entered.wait(), 5)
            deactivation = asyncio.create_task(
                self.client.patch(
                    f"/api/console/inventory/warehouses/{self.warehouse['id']}",
                    headers=self.headers,
                    json={"is_active": False},
                )
            )
            try:
                await asyncio.sleep(0.05)
                self.assertFalse(deactivation.done())
            finally:
                release.set()
            confirmed, updated = await asyncio.gather(confirmation, deactivation)
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(confirmed.json()["status"], "CONFIRMED")
