"""Физические проекции, прослеживаемость и защита справочников на PostgreSQL."""

import os
import unittest
from dataclasses import replace
from decimal import Decimal
from uuid import UUID, uuid4
from unittest.mock import patch
from sqlalchemy import delete, insert
from test import test_inventory_receipt_posting_postgres as support
from src.modules.inventory.presentation.stock_position.router import (
    router as positions_router,
    balances_router,
)
from src.modules.inventory.presentation.stock_posting.router import movements_router
from src.modules.inventory.infrastructure.persistence.models.stock_receipt_posting_requests import (
    ReceiptPostingRequestModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_positions import (
    StockPositionModel,
)
from src.modules.inventory.infrastructure.stock_posting.persistence.query_repository import (
    SqlAlchemyStockPostingQueryRepository,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class StockReadPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет настоящие HTTP, SQL и UoW без повторного запуска унаследованных тестов."""

    drop_schemas = support.ReceiptPostingPostgresTests.drop_schemas
    create_receipt = support.ReceiptPostingPostgresTests.create_receipt
    location_for = support.ReceiptPostingPostgresTests.location_for
    confirmed = support.ReceiptPostingPostgresTests.confirmed
    row = support.ReceiptPostingPostgresTests.row
    receive = support.ReceiptPostingPostgresTests.receive
    counts = support.ReceiptPostingPostgresTests.counts

    async def asyncSetUp(self) -> None:
        """Собирает реальные справочники, проведение и read-side маршруты."""
        await support.ReceiptPostingPostgresTests.asyncSetUp(self)
        self.app.include_router(positions_router, prefix="/api/console")
        self.app.include_router(balances_router, prefix="/api/console")
        self.app.include_router(movements_router, prefix="/api/console")
        self.root = "/api/console/inventory"

    async def read(self, path: str, **params: object):
        """Читает endpoint с проверкой успешного ответа."""
        response = await self.client.get(self.root + path, params=params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def posted(self, quantity: str = "1.5") -> tuple[dict, dict]:
        """Создаёт проведённый факт с известной точной величиной."""
        document = await self.confirmed(quantity=quantity)
        response = await self.receive(document, [self.row(document, quantity)])
        self.assertEqual(response.status_code, 201, response.text)
        return document, response.json()

    async def test_grouped_ledger_filters_full_path_and_normalized_details(
        self,
    ) -> None:
        """Два факта одной позиции дают одну запись журнала; данные читаются без command result."""
        document = await self.confirmed(quantity="1.25")
        rows = [self.row(document, "500"), self.row(document, "750")]
        for row in rows:
            row["uom"] = "G"
        posted = await self.receive(
            document,
            rows,
            costs=[
                {
                    "amount": "0",
                    "currency": "USD",
                    "allocations": [
                        {"client_line_id": rows[0]["client_line_id"], "amount": "0"}
                    ],
                }
            ],
        )
        self.assertEqual(posted.status_code, 201, posted.text)
        fact = posted.json()
        pid = fact["positions"][0]["id"]
        page = await self.read("/stock-positions")
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["items"][0]["on_hand_qty"], "1.250")
        for field, value in [
            ("warehouse_id", self.warehouse["id"]),
            ("location_id", self.location["id"]),
            ("inventory_item_id", self.item["id"]),
            ("owner_id", self.company["id"]),
            ("stock_status", "SELLABLE"),
        ]:
            self.assertEqual(
                (await self.read("/stock-positions", **{field: value}))["total"], 1
            )
            for resource in ["stock-movements", "stock-executions", "stock-postings"]:
                self.assertEqual(
                    (await self.read("/" + resource, **{field: value}))["total"], 1
                )
        movement = await self.read("/stock-movements", position_id=pid, limit=1)
        self.assertEqual(movement["position"]["version"], 1)
        self.assertEqual(len(movement["items"][0]["execution_line_ids"]), 2)
        self.assertEqual(movement["items"][0]["document_id"], document["id"])
        card = await self.read("/stock-positions/" + pid)
        self.assertEqual(Decimal(card["ledger_quantity"]), Decimal(card["on_hand_qty"]))
        for resource, identifier in [
            ("stock-executions", fact["execution_id"]),
            ("stock-postings", fact["posting_id"]),
        ]:
            detail = await self.read(f"/{resource}/{identifier}/details")
            self.assertEqual(len(detail["lines"]), 2)
            self.assertEqual(len(detail["ledger"]), 1)
            self.assertEqual(detail["costs"][0]["amount"], "0.0000")
            self.assertEqual(len(detail["ledger"][0]["execution_line_ids"]), 2)
        async with self.engine.begin() as c:
            await bind_tenant_schema(c, self.tenant.uuid, self.naming)
            await c.execute(
                delete(ReceiptPostingRequestModel).where(
                    ReceiptPostingRequestModel.execution_id
                    == UUID(fact["execution_id"])
                )
            )
        detail = await self.read(f"/stock-executions/{fact['execution_id']}/details")
        self.assertFalse(detail["has_receipt_result"])
        self.assertEqual(len(detail["ledger"]), 1)
        self.assertEqual(Decimal(detail["lines"][0]["quantity"]), Decimal(".5"))
        self.assertEqual((await self.read("/stock-movements"))["total"], 1)

    async def test_precision_zero_positions_and_accounting_settings(self) -> None:
        """Точный остаток не округляется; совместимые изменения разрешены, несовместимые отклоняются."""
        exact = "1234567890.1234567890123456789"
        document, fact = await self.posted(exact)
        self.assertEqual(
            (await self.read("/stock-positions"))["items"][0]["on_hand_qty"], exact
        )
        url = f"{self.root}/items/{self.item['id']}"
        response = await self.client.patch(
            url, headers=self.headers, json={"quantity_rules": {"step": "1"}}
        )
        self.assertEqual(response.status_code, 409, response.text)
        response = await self.client.patch(
            url, headers=self.headers, json={"sku": "RENAMED"}
        )
        self.assertEqual(response.status_code, 200, response.text)
        details = await self.read(f"/stock-executions/{fact['execution_id']}/details")
        self.assertEqual(details["lines"][0]["sku"], "renamed")
        self.assertEqual(details["lines"][0]["sku_at_receipt"], self.item["sku"])
        unused_owner_response = await self.client.post(
            "/api/console/crm/companies",
            headers=self.headers,
            json={"legal_name": "Zero owner"},
        )
        self.assertEqual(
            unused_owner_response.status_code, 201, unused_owner_response.text
        )
        unused_owner = unused_owner_response.json()
        empty_item = (
            await self.client.post(
                self.root + "/items", headers=self.headers, json={"sku": "ZERO"}
            )
        ).json()
        async with self.engine.begin() as c:
            await bind_tenant_schema(c, self.tenant.uuid, self.naming)
            await c.execute(
                insert(StockPositionModel).values(
                    id=uuid4(),
                    inventory_item_id=UUID(empty_item["id"]),
                    location_id=UUID(self.location["id"]),
                    owner_id=UUID(unused_owner["id"]),
                    lot_id=None,
                    serial_id=None,
                    stock_status="SELLABLE",
                    base_uom="PCS",
                    on_hand_qty=0,
                    version=0,
                )
            )
        self.assertEqual(
            (await self.read("/stock-positions", inventory_item_id=empty_item["id"]))[
                "total"
            ],
            0,
        )
        self.assertEqual(
            (
                await self.read(
                    "/stock-positions",
                    inventory_item_id=empty_item["id"],
                    include_zero="true",
                )
            )["total"],
            1,
        )
        self.assertEqual(
            (
                await self.client.delete(
                    self.root + "/items/" + empty_item["id"], headers=self.headers
                )
            ).status_code,
            409,
        )
        response = await self.client.patch(
            self.root + "/items/" + empty_item["id"],
            headers=self.headers,
            json={"base_uom": "KG"},
        )
        self.assertEqual(response.status_code, 409, response.text)

        owner_delete = await self.client.delete(
            "/api/console/crm/companies/" + unused_owner["id"], headers=self.headers
        )
        self.assertEqual(owner_delete.status_code, 409, owner_delete.text)

    async def test_required_dates_guards_and_inactive_history(self) -> None:
        """Положительный REQUIRED-запас сохраняет срок; деактивация не скрывает физическое количество."""
        item = (
            await self.client.post(
                self.root + "/items",
                headers=self.headers,
                json={
                    "sku": "EXP",
                    "tracking_mode": "LOT",
                    "expiration_mode": "REQUIRED",
                },
            )
        ).json()
        lots = f"{self.root}/items/{item['id']}/lots"
        lot = (
            await self.client.post(
                lots,
                headers=self.headers,
                json={"number": "000Lot", "expires_on": "2020-01-01"},
            )
        ).json()
        doc = await self.confirmed(item)
        result = await self.receive(doc, [self.row(doc, lot_id=lot["id"])])
        self.assertEqual(result.status_code, 201, result.text)
        response = await self.client.patch(
            lots + "/" + lot["id"], headers=self.headers, json={"expires_on": None}
        )
        self.assertEqual(response.status_code, 409, response.text)
        response = await self.client.patch(
            self.root + "/items/" + item["id"],
            headers=self.headers,
            json={"expiration_mode": "NONE"},
        )
        self.assertEqual(response.status_code, 409, response.text)
        response = await self.client.patch(
            lots + "/" + lot["id"],
            headers=self.headers,
            json={"expires_on": "2028-01-01"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        await self.client.patch(
            self.root + "/warehouses/" + self.warehouse["id"],
            headers=self.headers,
            json={"is_active": False},
        )
        page = await self.read("/stock-positions", lot_id=lot["id"])
        self.assertEqual(page["total"], 1)
        self.assertFalse(page["items"][0]["warehouse_is_active"])
        self.assertEqual(page["items"][0]["expires_on"], "2028-01-01")
        self.assertEqual(
            (await self.read("/stock-movements", lot_id=lot["id"]))["total"], 1
        )

    async def test_journal_retries_if_position_changes_during_read(self) -> None:
        """Составное чтение не смешивает прежнюю версию остатка с новой историей."""
        doc = await self.confirmed(quantity="2")
        a = await self.receive(doc, [self.row(doc, "1")])
        fact = a.json()
        pid = fact["positions"][0]["id"]
        remaining = (await self.client.get(self.receipts + "/" + doc["id"])).json()
        original = SqlAlchemyStockPostingQueryRepository._read_movements
        changed = False

        async def read_and_post(repository, query, snapshot):
            nonlocal changed
            result = await original(repository, query, snapshot)
            if not changed:
                changed = True
                response = await self.receive(remaining, [self.row(remaining, "1")])
                self.assertEqual(response.status_code, 201, response.text)
            return result

        with patch.object(
            SqlAlchemyStockPostingQueryRepository, "_read_movements", read_and_post
        ):
            page = await self.read("/stock-movements", position_id=pid)
        self.assertEqual(page["position"]["version"], 2)
        self.assertEqual(page["total"], 2)
        self.assertEqual(Decimal(page["position"]["quantity"]), Decimal("2"))

    async def test_auth_tenant_pagination_and_literal_search(self) -> None:
        """Изоляция действует для всех чтений; периоды и параметры валидируются в Presentation."""
        _, fact = await self.posted()
        for resource in [
            "stock-positions",
            "stock-movements",
            "stock-executions",
            "stock-postings",
        ]:
            page = await self.read("/" + resource, offset=100)
            self.assertEqual(page["items"], [])
            self.assertEqual(page["total"], 1)
            self.assertEqual((await self.read("/" + resource, search="%"))["total"], 0)
        self.assertEqual(
            (
                await self.client.get(
                    self.root + "/stock-movements",
                    params={
                        "posted_from": "2026-01-01T00:00:00Z",
                        "posted_to": "2025-01-01T00:00:00Z",
                    },
                )
            ).status_code,
            422,
        )
        original = self.app.state.test_context
        self.app.state.test_context = replace(
            original, principal=replace(original.principal, tenant_id=str(self.other))
        )
        try:
            for resource in [
                "stock-positions",
                "stock-movements",
                "stock-executions",
                "stock-postings",
            ]:
                self.assertEqual((await self.read("/" + resource))["total"], 0)
            self.assertEqual(
                (
                    await self.client.get(
                        self.root
                        + "/stock-executions/"
                        + fact["execution_id"]
                        + "/details"
                    )
                ).status_code,
                404,
            )
        finally:
            self.app.state.test_context = original
        self.app.state.test_context = replace(original, principal=None)
        try:
            self.assertEqual(
                (await self.client.get(self.root + "/stock-positions")).status_code, 401
            )
        finally:
            self.app.state.test_context = original

    async def test_fact_filters_match_one_line_and_serial_dimensions(self) -> None:
        """Фильтры заголовка совпадают в одной фактической строке; серия сохраняет источник дат LOT."""
        item = (
            await self.client.post(
                self.root + "/items",
                headers=self.headers,
                json={
                    "sku": "TRACE",
                    "tracking_mode": "LOT_AND_SERIAL",
                    "expiration_mode": "REQUIRED",
                },
            )
        ).json()
        lot = (
            await self.client.post(
                f"{self.root}/items/{item['id']}/lots",
                headers=self.headers,
                json={"number": "000L", "expires_on": "2028-01-01"},
            )
        ).json()
        serial = (
            await self.client.post(
                f"{self.root}/items/{item['id']}/serials",
                headers=self.headers,
                json={"number": "000Sn", "lot_id": lot["id"]},
            )
        ).json()
        other_location = await self.location_for(self.warehouse["id"], "B1")
        doc = await self.create_receipt(
            {
                "warehouse_id": self.warehouse["id"],
                "owner_id": self.company["id"],
                "lines": [
                    {
                        "inventory_item_id": self.item["id"],
                        "quantity": "1",
                        "uom": "KG",
                    },
                    {"inventory_item_id": item["id"], "quantity": "1", "uom": "PCS"},
                ],
            }
        )
        doc = (
            await self.client.post(
                self.receipts + "/" + doc["id"] + "/confirm",
                headers=self.headers,
                json={"expected_version": doc["version"]},
            )
        ).json()
        first = self.row(doc, "1")
        second = self.row(doc, "1", lot_id=lot["id"], serial_id=serial["id"])
        second.update(
            document_line_id=doc["lines"][1]["id"],
            uom="PCS",
            location_id=other_location["id"],
        )
        response = await self.receive(doc, [first, second])
        self.assertEqual(response.status_code, 201, response.text)
        for resource in ["stock-executions", "stock-postings"]:
            self.assertEqual(
                (
                    await self.read(
                        "/" + resource,
                        inventory_item_id=self.item["id"],
                        location_id=other_location["id"],
                    )
                )["total"],
                0,
            )
            self.assertEqual(
                (
                    await self.read(
                        "/" + resource,
                        inventory_item_id=item["id"],
                        location_id=other_location["id"],
                    )
                )["total"],
                1,
            )
        for resource in [
            "stock-positions",
            "stock-movements",
            "stock-executions",
            "stock-postings",
        ]:
            self.assertEqual(
                (
                    await self.read(
                        "/" + resource, serial_id=serial["id"], lot_id=lot["id"]
                    )
                )["total"],
                1,
            )
        position = (await self.read("/stock-positions", serial_id=serial["id"]))[
            "items"
        ][0]
        self.assertEqual(position["expires_on"], "2028-01-01")
        changed = await self.client.patch(
            f"{self.root}/items/{item['id']}/serials/{serial['id']}",
            headers=self.headers,
            json={"number": "000Sn-fixed"},
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        detail = await self.read(
            f"/stock-executions/{response.json()['execution_id']}/details"
        )
        self.assertEqual(detail["lines"][1]["serial_number"], "000Sn-fixed")
        self.assertEqual(detail["lines"][1]["serial_number_at_receipt"], "000Sn")

    async def test_settings_update_waits_for_receipt_and_checks_committed_quantity(
        self,
    ) -> None:
        """Параллельная смена шага ждёт корень SKU и проверяет уже проведённое количество."""
        import asyncio
        from src.modules.inventory.infrastructure.stock_execution.persistence.repository import (
            SqlAlchemyStockExecutionRepository,
        )

        document = await self.confirmed(quantity="1.5")
        entered, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyStockExecutionRepository.add

        async def held(repository, execution):
            entered.set()
            await release.wait()
            await original(repository, execution)

        with patch.object(SqlAlchemyStockExecutionRepository, "add", held):
            receipt = asyncio.create_task(
                self.receive(document, [self.row(document, "1.5")])
            )
            await asyncio.wait_for(entered.wait(), 5)
            update = asyncio.create_task(
                self.client.patch(
                    self.root + "/items/" + self.item["id"],
                    headers=self.headers,
                    json={"quantity_rules": {"step": "1"}},
                )
            )
            try:
                await asyncio.sleep(0.05)
                self.assertFalse(update.done())
            finally:
                release.set()
            posted, changed = await asyncio.gather(receipt, update)
        self.assertEqual(posted.status_code, 201, posted.text)
        self.assertEqual(changed.status_code, 409, changed.text)
        compatible = await self.client.patch(
            self.root + "/items/" + self.item["id"],
            headers=self.headers,
            json={"quantity_rules": {"step": "0.5"}},
        )
        self.assertEqual(compatible.status_code, 200, compatible.text)

    async def test_balances_aggregate_lots_and_serials_with_optional_detail(
        self,
    ) -> None:
        """Сводка объединяет серии одного SKU, а LOT/SERIAL независимо добавляют измерения группировки."""
        item = (
            await self.client.post(
                self.root + "/items",
                headers=self.headers,
                json={"sku": "SUMMARY", "tracking_mode": "LOT_AND_SERIAL"},
            )
        ).json()
        lots = []
        for number in ["000A", "000B"]:
            lots.append(
                (
                    await self.client.post(
                        f"{self.root}/items/{item['id']}/lots",
                        headers=self.headers,
                        json={"number": number},
                    )
                ).json()
            )
        serials = []
        for index, lot in enumerate([lots[0], lots[0], lots[1]]):
            serials.append(
                (
                    await self.client.post(
                        f"{self.root}/items/{item['id']}/serials",
                        headers=self.headers,
                        json={"number": f"000Sn-{index}", "lot_id": lot["id"]},
                    )
                ).json()
            )
        doc = await self.confirmed(item, "3")
        rows = [
            self.row(doc, "1", lot_id=serial["lot_id"], serial_id=serial["id"])
            for serial in serials
        ]
        response = await self.receive(doc, rows)
        self.assertEqual(response.status_code, 201, response.text)
        summary = await self.read("/stock-balances", inventory_item_id=item["id"])
        self.assertEqual(summary["total"], 1)
        row = summary["items"][0]
        self.assertEqual(Decimal(row["on_hand_qty"]), Decimal("3"))
        self.assertEqual(row["position_count"], 3)
        self.assertEqual(row["lot_count"], 2)
        self.assertEqual(row["serial_count"], 3)
        self.assertIsNone(row["lot_id"])
        self.assertIsNone(row["serial_id"])
        self.assertNotIn("id", row)
        bylot = await self.read(
            "/stock-balances", inventory_item_id=item["id"], group_by_lot="true"
        )
        self.assertEqual(bylot["total"], 2)
        self.assertEqual(
            sorted(Decimal(r["on_hand_qty"]) for r in bylot["items"]),
            [Decimal(1), Decimal(2)],
        )
        byserial = await self.read(
            "/stock-balances", inventory_item_id=item["id"], group_by_serial="true"
        )
        self.assertEqual(byserial["total"], 3)
        self.assertEqual(len({r["key"] for r in byserial["items"]}), 3)
        both = await self.read(
            "/stock-balances",
            inventory_item_id=item["id"],
            group_by_serial="true",
            group_by_lot="true",
            limit=1,
            offset=1,
        )
        self.assertEqual(both["total"], 3)
        self.assertEqual(len(both["items"]), 1)
        self.assertIsNotNone(both["items"][0]["lot_id"])
        searched = await self.read(
            "/stock-balances", inventory_item_id=item["id"], search="000B"
        )
        self.assertEqual(searched["total"], 1)
        self.assertEqual(Decimal(searched["items"][0]["on_hand_qty"]), Decimal(1))
        filtered = await self.read(
            "/stock-balances", inventory_item_id=item["id"], lot_id=lots[0]["id"]
        )
        self.assertEqual(Decimal(filtered["items"][0]["on_hand_qty"]), Decimal(2))

    async def test_summary_keeps_all_decimal_digits_across_lots(self) -> None:
        """Сумма разных партий вычисляется без округления и без объединения несовместимых единиц."""
        item = (
            await self.client.post(
                self.root + "/items",
                headers=self.headers,
                json={
                    "sku": "DECIMAL-SUM",
                    "base_uom": "KG",
                    "tracking_mode": "LOT",
                    "quantity_rules": {"step": "0.0000000000000000001"},
                },
            )
        ).json()
        lots = []
        for number in ("A", "B"):
            lots.append(
                (
                    await self.client.post(
                        f"{self.root}/items/{item['id']}/lots",
                        headers=self.headers,
                        json={"number": number},
                    )
                ).json()
            )
        expected = "1234567891.1234567890123456790"
        doc = await self.confirmed(item, expected)
        rows = [
            self.row(doc, "1234567890.1234567890123456789", lot_id=lots[0]["id"]),
            self.row(doc, "1.0000000000000000001", lot_id=lots[1]["id"]),
        ]
        result = await self.receive(doc, rows)
        self.assertEqual(result.status_code, 201, result.text)
        page = await self.read("/stock-balances", inventory_item_id=item["id"])
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["items"][0]["on_hand_qty"], expected)
        self.assertEqual(page["items"][0]["position_count"], 2)
        self.assertEqual(page["items"][0]["base_uom"], "KG")
