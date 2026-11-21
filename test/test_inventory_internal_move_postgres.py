"""Проверяет атомарные обе стороны INTERNAL_MOVE на настоящем PostgreSQL."""

import asyncio
import os
import unittest
from decimal import Decimal
from uuid import uuid4
from httpx import Response
from test.test_inventory_stock_issue_postgres import StockIssuePostgresTests as Support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется отдельная PostgreSQL БД."
)
class InternalMovePostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет документ, две стороны Ledger и физическую сохранность запаса."""

    drop_schemas = Support.drop_schemas
    create_receipt = Support.create_receipt
    location_for = Support.location_for
    confirmed = Support.confirmed
    row = Support.row
    receive = Support.receive
    counts = Support.counts
    read = Support.read

    async def asyncSetUp(self) -> None:
        """Поднимает общий HTTP-контур и создаёт 100 KG в исходной локации."""
        await Support.asyncSetUp(self)
        self.moves = self.root + "/stock-documents/internal-moves"
        self.destination = await self.location_for(self.warehouse["id"], "B2")

    async def plan(self, quantity: str = "80", *, item: dict | None = None) -> dict:
        """Создаёт подтверждённый план без изменения физического количества."""
        item = item or self.item
        response = await self.client.post(
            self.moves,
            headers={**self.headers, "Idempotency-Key": str(uuid4())},
            json={
                "warehouse_id": self.warehouse["id"],
                "owner_id": self.company["id"],
                "lines": [
                    {
                        "inventory_item_id": item["id"],
                        "quantity": quantity,
                        "uom": item["base_uom"],
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        document = response.json()
        self.assertEqual(document["operation_type"], "INTERNAL_MOVE")
        response = await self.client.post(
            f"{self.moves}/{document['id']}/confirm",
            headers=self.headers,
            json={"expected_version": document["version"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def actual(
        self,
        document: dict,
        quantity: str,
        *,
        source: str | None = None,
        destination: str | None = None,
    ) -> dict:
        """Указывает существующий источник и единственное изменяемое измерение назначения."""
        return {
            "client_line_id": str(uuid4()),
            "document_line_id": document["lines"][0]["id"],
            "source_position_id": source or self.position_id,
            "destination_location_id": destination or self.destination["id"],
            "quantity": quantity,
            "uom": document["lines"][0]["base_uom"],
        }

    async def move(
        self, document: dict, rows: list[dict], key: str | None = None
    ) -> Response:
        """Проводит обе стороны с единственным ключом команды."""
        return await self.client.post(
            f"{self.moves}/{document['id']}/move",
            headers={**self.headers, "Idempotency-Key": key or str(uuid4())},
            json={"expected_version": document["version"], "lines": rows},
        )

    async def test_partial_move_balance_history_read_and_replay(self) -> None:
        """Частичные 30 и 50 сохраняют общий запас 100, связи обеих сторон и исходный результат."""
        document = await self.plan()
        original = document
        rows = [self.actual(document, "30")]
        key = str(uuid4())
        first = await self.move(document, rows, key)
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(first.json()["document_status"], "PARTIALLY_EXECUTED")
        self.assertEqual(
            sorted(Decimal(e["quantity_delta"]) for e in first.json()["ledger"]),
            [Decimal(-30), Decimal(30)],
        )
        document = (await self.client.get(f"{self.moves}/{document['id']}")).json()
        self.assertEqual(Decimal(document["lines"][0]["executed_qty"]), Decimal(30))
        second = await self.move(document, [self.actual(document, "50")])
        self.assertEqual(second.status_code, 201, second.text)
        self.assertEqual(second.json()["document_status"], "COMPLETED")
        positions = await self.read(
            "/stock-positions", inventory_item_id=self.item["id"]
        )
        self.assertEqual(
            sorted(Decimal(p["on_hand_qty"]) for p in positions["items"]),
            [Decimal(20), Decimal(80)],
        )
        replay = await self.move(original, rows, key)
        self.assertEqual(replay.json(), first.json())
        result = await self.client.get(
            f"{self.root}/stock-executions/{first.json()['execution_id']}/internal-move-result"
        )
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json(), first.json())
        for loc in [self.location, self.destination]:
            facts = await self.read(
                "/stock-executions", document_id=document["id"], location_id=loc["id"]
            )
            self.assertEqual(facts["total"], 2)
        details = await self.read(
            f"/stock-executions/{first.json()['execution_id']}/details"
        )
        line = details["lines"][0]
        self.assertEqual(line["destination_location_id"], self.destination["id"])
        self.assertEqual(len(line["ledger_entry_ids"]), 2)
        self.assertNotEqual(
            line["source_ledger_entry_id"], line["destination_ledger_entry_id"]
        )
        history = await self.client.get(
            f"{self.moves}/{document['id']}/executions",
            params={"offset": "0", "limit": "1"},
        )
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(history.json()["total"], 2)

    async def test_insufficient_and_invalid_route_roll_back_destination(self) -> None:
        """Не создаёт целевой ноль при отказе и запрещает тот же адрес или другой склад."""
        document = await self.plan("200")
        before = await self.counts()
        response = await self.move(document, [self.actual(document, "101")])
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(
            response.json()["detail"]["code"], "insufficient_stock_quantity"
        )
        self.assertEqual(before, await self.counts())
        positions = await self.read(
            "/stock-positions", inventory_item_id=self.item["id"]
        )
        self.assertEqual(positions["total"], 1)
        same = await self.move(
            document, [self.actual(document, "1", destination=self.location["id"])]
        )
        self.assertEqual(same.status_code, 422, same.text)
        other = await self.client.post(
            self.root + "/warehouses",
            headers=self.headers,
            json={"code": "OTHER", "name": "Другой склад"},
        )
        self.assertEqual(other.status_code, 201, other.text)
        other_location = await self.location_for(other.json()["id"], "C3")
        wrong = await self.move(
            document, [self.actual(document, "1", destination=other_location["id"])]
        )
        self.assertEqual(wrong.status_code, 404, wrong.text)

    async def test_concurrency_and_key_protect_both_sides(self) -> None:
        """Параллельные документы не используют один запас дважды, повтор не создаёт новый приход."""
        documents = [await self.plan("70"), await self.plan("70")]
        responses = await asyncio.gather(
            *(self.move(d, [self.actual(d, "70")]) for d in documents)
        )
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [201, 409],
            [r.text for r in responses],
        )
        document = await self.plan("10")
        rows = [self.actual(document, "10")]
        key = str(uuid4())
        repeated = await asyncio.gather(
            *(self.move(document, rows, key) for _ in range(3))
        )
        self.assertEqual(
            [r.status_code for r in repeated], [201] * 3, [r.text for r in repeated]
        )
        self.assertEqual(len({r.json()["execution_id"] for r in repeated}), 1)
        changed = [self.actual(document, "10", destination=self.location["id"])]
        conflict = await self.move(document, changed, key)
        self.assertEqual(conflict.status_code, 409, conflict.text)

    async def test_destination_search_pagination_and_inactive(self) -> None:
        """Поиск адресов ограничен складом и активностью; строковые URL-параметры принимаются."""
        document = await self.plan("1")
        response = await self.client.get(
            f"{self.moves}/{document['id']}/destination-locations",
            params={"search": "B2", "offset": "0", "limit": "1"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["items"][0]["id"], self.destination["id"])
        changed = await self.client.patch(
            f"{self.root}/warehouses/{self.warehouse['id']}/locations/{self.destination['id']}",
            headers=self.headers,
            json={"is_active": False},
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        response = await self.client.get(
            f"{self.moves}/{document['id']}/destination-locations",
            params={"location_id": self.destination["id"]},
        )
        self.assertEqual(response.json()["items"], [])
        failed = await self.move(document, [self.actual(document, "1")])
        self.assertEqual(failed.status_code, 422, failed.text)

    async def test_serial_moves_to_destination_then_back(self) -> None:
        """Глобальный индекс сохраняет единственное присутствие LOT_AND_SERIAL на обеих выдачах."""
        response = await self.client.post(
            self.root + "/items",
            headers=self.headers,
            json={
                "sku": "MOVE-SERIAL",
                "base_uom": "PCS",
                "tracking_mode": "LOT_AND_SERIAL",
                "expiration_mode": "REQUIRED",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        item = response.json()
        lot = await self.client.post(
            f"{self.root}/items/{item['id']}/lots",
            headers=self.headers,
            json={"number": "000Lot-a", "expires_on": "2020-01-01"},
        )
        self.assertEqual(lot.status_code, 201, lot.text)
        serial = await self.client.post(
            f"{self.root}/items/{item['id']}/serials",
            headers=self.headers,
            json={"number": "000Serial-A", "lot_id": lot.json()["id"]},
        )
        self.assertEqual(serial.status_code, 201, serial.text)
        receipt = await self.confirmed(item, "1")
        posted = await self.receive(
            receipt,
            [
                self.row(
                    receipt, "1", lot_id=lot.json()["id"], serial_id=serial.json()["id"]
                )
            ],
        )
        self.assertEqual(posted.status_code, 201, posted.text)
        source = posted.json()["positions"][0]["id"]
        document = await self.plan("1", item=item)
        moved = await self.move(document, [self.actual(document, "1", source=source)])
        self.assertEqual(moved.status_code, 201, moved.text)
        destination = moved.json()["lines"][0]["destination_position_id"]
        self.assertEqual(moved.json()["lines"][0]["lot_id"], lot.json()["id"])
        stale = await self.plan("1", item=item)
        refused = await self.move(stale, [self.actual(stale, "1", source=source)])
        self.assertEqual(refused.status_code, 409, refused.text)
        self.assertEqual(
            refused.json()["detail"]["code"], "insufficient_stock_quantity"
        )
        reverse = await self.plan("1", item=item)
        returned = await self.move(
            reverse,
            [
                self.actual(
                    reverse, "1", source=destination, destination=self.location["id"]
                )
            ],
        )
        self.assertEqual(returned.status_code, 201, returned.text)
        positions = await self.read(
            "/stock-positions", serial_id=serial.json()["id"], include_zero=True
        )
        self.assertEqual(
            sorted(Decimal(p["on_hand_qty"]) for p in positions["items"]),
            [Decimal(0), Decimal(1)],
        )
        self.assertEqual(positions["total"], 2)

    async def test_multiple_routes_exact_units_and_existing_destination(self) -> None:
        """Объединяет однонаправленные источники точно и сохраняет отдельные маршруты факта."""
        document = await self.plan("30")
        rows = [self.actual(document, "10000"), self.actual(document, "20")]
        rows[0]["uom"] = "G"
        moved = await self.move(document, rows)
        self.assertEqual(moved.status_code, 201, moved.text)
        result = moved.json()
        self.assertEqual(len(result["ledger"]), 2)
        self.assertEqual(len(result["lines"]), 2)
        self.assertEqual(
            len({r["destination_ledger_entry_id"] for r in result["lines"]}), 1
        )
        second = await self.plan("5")
        response = await self.move(second, [self.actual(second, "5")])
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(
            result["lines"][0]["destination_position_id"],
            response.json()["lines"][0]["destination_position_id"],
        )
        self.assertEqual(
            Decimal(
                (
                    await self.read(
                        "/stock-positions/"
                        + response.json()["lines"][0]["destination_position_id"]
                    )
                )["on_hand_qty"]
            ),
            Decimal(35),
        )

    async def test_failure_after_outbox_rolls_back_and_key_can_retry(self) -> None:
        """Сбой фиксации результата после проводки и Outbox не оставляет ни одной стороны."""
        from unittest.mock import patch
        from src.modules.inventory.infrastructure.stock_document.persistence.internal_move_requests import (
            SqlAlchemyInternalMovePostingRequests,
        )

        document = await self.plan("10")
        rows = [self.actual(document, "10")]
        key = str(uuid4())
        before = await self.counts()
        with patch.object(
            SqlAlchemyInternalMovePostingRequests,
            "complete",
            side_effect=RuntimeError("test rollback after Outbox"),
        ):
            failed = await self.move(document, rows, key)
            self.assertEqual(failed.status_code, 500, failed.text)
        self.assertEqual(await self.counts(), before)
        positions = await self.read(
            "/stock-positions", inventory_item_id=self.item["id"]
        )
        self.assertEqual(positions["total"], 1)
        response = await self.move(document, rows, key)
        self.assertEqual(response.status_code, 201, response.text)

    async def test_opposing_position_routes_not_netted(self) -> None:
        """Запрещает использовать приход текущего исполнения как расход его другой строки."""
        first = await self.plan("10")
        moved = await self.move(first, [self.actual(first, "10")])
        self.assertEqual(moved.status_code, 201, moved.text)
        source_b = moved.json()["lines"][0]["destination_position_id"]
        c = await self.location_for(self.warehouse["id"], "C3")
        document = await self.plan("10")
        before = await self.counts()
        response = await self.move(
            document,
            [
                self.actual(document, "5"),
                self.actual(document, "5", source=source_b, destination=c["id"]),
            ],
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(before, await self.counts())

    async def test_version_and_plan_limits_protect_partial_progress(self) -> None:
        """Конкурентные факты одной версии не удваивают прогресс; свежая версия сохраняет лимит строки."""
        document = await self.plan("40")
        replies = await asyncio.gather(
            *(self.move(document, [self.actual(document, "30")]) for _ in range(2))
        )
        self.assertEqual(
            sorted(r.status_code for r in replies),
            [201, 409],
            [r.text for r in replies],
        )
        latest = (await self.client.get(f"{self.moves}/{document['id']}")).json()
        error = await self.move(latest, [self.actual(latest, "11")])
        self.assertEqual(error.status_code, 422, error.text)
        self.assertEqual(
            error.json()["detail"]["code"], "stock_document_line_over_execution"
        )
        result = await self.move(latest, [self.actual(latest, "10")])
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(result.json()["document_status"], "COMPLETED")

    async def test_draft_lifecycle_replay_and_measurement_injection(self) -> None:
        """План редактируется до подтверждения, отменяется без исполнения и не принимает подмену измерений."""
        key = str(uuid4())
        payload = {
            "warehouse_id": self.warehouse["id"],
            "owner_id": self.company["id"],
            "lines": [],
        }
        response = await self.client.post(
            self.moves, headers={**self.headers, "Idempotency-Key": key}, json=payload
        )
        self.assertEqual(response.status_code, 201, response.text)
        original = response.json()
        patched = await self.client.patch(
            f"{self.moves}/{original['id']}",
            headers=self.headers,
            json={
                "expected_version": original["version"],
                "lines": [
                    {"inventory_item_id": self.item["id"], "quantity": "3", "uom": "KG"}
                ],
            },
        )
        self.assertEqual(patched.status_code, 200, patched.text)
        document = patched.json()
        confirmed = await self.client.post(
            f"{self.moves}/{document['id']}/confirm",
            headers=self.headers,
            json={"expected_version": document["version"]},
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        document = confirmed.json()
        row = self.actual(document, "1")
        row["stock_status"] = "DAMAGED"
        invalid = await self.move(document, [row])
        self.assertEqual(invalid.status_code, 422, invalid.text)
        cancelled = await self.client.post(
            f"{self.moves}/{document['id']}/cancel",
            headers=self.headers,
            json={"expected_version": document["version"]},
        )
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        replay = await self.client.post(
            self.moves, headers={**self.headers, "Idempotency-Key": key}, json=payload
        )
        self.assertEqual(replay.json(), original)
        refused = await self.move(cancelled.json(), [self.actual(document, "1")])
        self.assertEqual(refused.status_code, 409, refused.text)

    async def test_serial_without_lot_and_repeated_identity(self) -> None:
        """SERIAL сохраняется без партии и дат; повтор экземпляра в одном факте запрещён."""
        response = await self.client.post(
            self.root + "/items",
            headers=self.headers,
            json={"sku": "ONLY-SERIAL", "base_uom": "PCS", "tracking_mode": "SERIAL"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        item = response.json()
        serial = await self.client.post(
            f"{self.root}/items/{item['id']}/serials",
            headers=self.headers,
            json={"number": "000Ser"},
        )
        self.assertEqual(serial.status_code, 201, serial.text)
        receipt = await self.confirmed(item, "1")
        posted = await self.receive(
            receipt, [self.row(receipt, "1", serial_id=serial.json()["id"])]
        )
        self.assertEqual(posted.status_code, 201, posted.text)
        source = posted.json()["positions"][0]["id"]
        document = await self.plan("2", item=item)
        invalid = await self.move(
            document,
            [
                self.actual(document, "1", source=source),
                self.actual(document, "1", source=source),
            ],
        )
        self.assertEqual(invalid.status_code, 422, invalid.text)
        result = await self.move(document, [self.actual(document, "1", source=source)])
        self.assertEqual(result.status_code, 201, result.text)
        self.assertIsNone(result.json()["lines"][0]["lot_id"])
        self.assertEqual(result.json()["lines"][0]["serial_id"], serial.json()["id"])

    async def test_opposite_documents_share_stable_lock_order(self) -> None:
        """Одновременные A→B и B→A сохраняют баланс и не блокируют друг друга циклически."""
        seed = await self.plan("10")
        first = await self.move(seed, [self.actual(seed, "10")])
        self.assertEqual(first.status_code, 201, first.text)
        source_b = first.json()["lines"][0]["destination_position_id"]
        forward, reverse = await self.plan("20"), await self.plan("5")
        responses = await asyncio.wait_for(
            asyncio.gather(
                self.move(forward, [self.actual(forward, "20")]),
                self.move(
                    reverse,
                    [
                        self.actual(
                            reverse,
                            "5",
                            source=source_b,
                            destination=self.location["id"],
                        )
                    ],
                ),
            ),
            timeout=10,
        )
        self.assertEqual(
            [r.status_code for r in responses], [201, 201], [r.text for r in responses]
        )
        page = await self.read("/stock-positions", inventory_item_id=self.item["id"])
        self.assertEqual(
            sorted(Decimal(v["on_hand_qty"]) for v in page["items"]),
            [Decimal(25), Decimal(75)],
        )

    async def test_wrong_sku_missing_source_and_destination_traceability(self) -> None:
        """Выбор источника проверяется по SKU; карточка проведения раскрывает адрес назначения."""
        response = await self.client.post(
            self.root + "/items",
            headers=self.headers,
            json={"sku": "WRONG-ITEM", "base_uom": "KG"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        wrong = await self.plan("1", item=response.json())
        failed = await self.move(wrong, [self.actual(wrong, "1")])
        self.assertEqual(failed.status_code, 422, failed.text)
        missing = await self.move(wrong, [self.actual(wrong, "1", source=str(uuid4()))])
        self.assertEqual(missing.status_code, 404, missing.text)
        document = await self.plan("1")
        result = await self.move(document, [self.actual(document, "1")])
        self.assertEqual(result.status_code, 201, result.text)
        details = await self.read(
            f"/stock-postings/{result.json()['posting_id']}/details"
        )
        self.assertEqual(
            details["lines"][0]["destination_location_id"], self.destination["id"]
        )
        movements = await self.read("/stock-movements", document_id=document["id"])
        self.assertEqual(movements["total"], 2)
