"""Ручной ISSUE: реальный tenant-UoW, исходные позиции и отрицательный Ledger."""

import asyncio
import os
import unittest
from decimal import Decimal
from uuid import uuid4
from httpx import Response
from test.test_inventory_stock_read_postgres import StockReadPostgresTests as Support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется отдельная PostgreSQL БД."
)
class StockIssuePostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет полный HTTP-путь физического расхода без заказа или резерва."""

    drop_schemas = Support.drop_schemas
    create_receipt = Support.create_receipt
    location_for = Support.location_for
    confirmed = Support.confirmed
    row = Support.row
    receive = Support.receive
    counts = Support.counts
    read = Support.read

    async def asyncSetUp(self) -> None:
        """Создаёт реальные справочники и запас 100 KG существующей приёмкой."""
        await Support.asyncSetUp(self)
        self.issues = self.root + "/stock-documents/issues"
        document = await self.confirmed(quantity="100")
        response = await self.receive(document, [self.row(document, "100")])
        self.assertEqual(response.status_code, 201, response.text)
        self.position_id = response.json()["positions"][0]["id"]

    async def issue_document(
        self, quantity: str = "80", *, item: dict | None = None
    ) -> dict:
        """Создаёт и подтверждает независимый план ISSUE."""
        item = item or self.item
        response = await self.client.post(
            self.issues,
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
        self.assertEqual(document["operation_type"], "ISSUE")
        confirmed = await self.client.post(
            f"{self.issues}/{document['id']}/confirm",
            headers=self.headers,
            json={"expected_version": document["version"]},
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        return confirmed.json()

    def actual(
        self, document: dict, quantity: str, position_id: str | None = None
    ) -> dict:
        """Формирует отдельное распределение исходной позиции строке плана."""
        return {
            "client_line_id": str(uuid4()),
            "document_line_id": document["lines"][0]["id"],
            "source_position_id": position_id or self.position_id,
            "quantity": quantity,
            "uom": document["lines"][0]["base_uom"],
        }

    async def issue(
        self, document: dict, rows: list[dict], key: str | None = None
    ) -> Response:
        """Отправляет один атомарный факт с обязательным ключом."""
        return await self.client.post(
            f"{self.issues}/{document['id']}/issue",
            headers={**self.headers, "Idempotency-Key": key or str(uuid4())},
            json={"expected_version": document["version"], "lines": rows},
        )

    async def test_partial_issue_30_50_and_late_replay(self) -> None:
        """Две выдачи уменьшают 100 до 20; повтор старой команды не меняет последующий запас."""
        document = await self.issue_document()
        original = document
        rows = [self.actual(document, "30")]
        key = str(uuid4())
        first = await self.issue(document, rows, key)
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(first.json()["document_status"], "PARTIALLY_EXECUTED")
        document = (await self.client.get(f"{self.issues}/{document['id']}")).json()
        self.assertEqual(Decimal(document["lines"][0]["remaining_qty"]), Decimal("50"))
        second = await self.issue(document, [self.actual(document, "50")])
        self.assertEqual(second.status_code, 201, second.text)
        self.assertEqual(second.json()["document_status"], "COMPLETED")
        self.assertEqual(
            Decimal(second.json()["positions"][0]["after_quantity"]), Decimal("20")
        )
        self.assertEqual(
            Decimal(second.json()["ledger"][0]["quantity_delta"]), Decimal("-50")
        )
        replay = await self.issue(original, rows, key)
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(replay.json(), first.json())
        history = (
            await self.client.get(f"{self.issues}/{document['id']}/executions")
        ).json()
        self.assertEqual(history["total"], 2)
        self.assertEqual(
            [Decimal(v["lines"][0]["quantity"]) for v in history["items"]],
            [Decimal("50"), Decimal("30")],
        )
        position = await self.read("/stock-positions/" + self.position_id)
        self.assertEqual(Decimal(position["on_hand_qty"]), Decimal("20"))
        movement = await self.read("/stock-movements", document_id=document["id"])
        self.assertEqual(movement["total"], 2)

    async def test_insufficient_stock_rolls_back_and_keeps_source(self) -> None:
        """План может превышать запас; проведение 101 из 100 откатывает все учётные изменения."""
        document = await self.issue_document("200")
        response = await self.issue(
            document, [self.actual(document, "60"), self.actual(document, "41")]
        )
        self.assertEqual(response.status_code, 409, response.text)
        error = response.json()["detail"]
        self.assertEqual(error["code"], "insufficient_stock_quantity")
        self.assertEqual(Decimal(error["requested_quantity"]), Decimal("101"))
        self.assertEqual(Decimal(error["current_quantity"]), Decimal("100"))
        self.assertEqual(
            (await self.client.get(f"{self.issues}/{document['id']}")).json(), document
        )
        history = (
            await self.client.get(f"{self.issues}/{document['id']}/executions")
        ).json()
        self.assertEqual(history["total"], 0)
        self.assertEqual(
            Decimal(
                (await self.read("/stock-positions/" + self.position_id))["on_hand_qty"]
            ),
            Decimal("100"),
        )

    async def test_concurrent_documents_cannot_make_negative_stock(self) -> None:
        """Два независимых плана не списывают по 70 из общего физического запаса 100."""
        documents = [await self.issue_document("70"), await self.issue_document("70")]
        responses = await asyncio.gather(
            *(self.issue(doc, [self.actual(doc, "70")]) for doc in documents)
        )
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [201, 409],
            [r.text for r in responses],
        )
        error = next(r for r in responses if r.status_code == 409).json()["detail"]
        self.assertEqual(error["code"], "insufficient_stock_quantity")
        self.assertEqual(
            Decimal(
                (await self.read("/stock-positions/" + self.position_id))["on_hand_qty"]
            ),
            Decimal("30"),
        )

    async def test_same_key_concurrent_requests_create_one_issue(self) -> None:
        """Параллельный повтор возвращает один исходный результат."""
        document = await self.issue_document("10")
        rows = [self.actual(document, "10")]
        key = str(uuid4())
        responses = await asyncio.gather(
            *(self.issue(document, rows, key) for _ in range(3))
        )
        self.assertEqual(
            [r.status_code for r in responses], [201] * 3, [r.text for r in responses]
        )
        self.assertEqual(len({r.json()["execution_id"] for r in responses}), 1)
        changed = await self.issue(document, [self.actual(document, "1")], key)
        self.assertEqual(changed.status_code, 409, changed.text)
        self.assertEqual(
            Decimal(
                (await self.read("/stock-positions/" + self.position_id))["on_hand_qty"]
            ),
            Decimal("90"),
        )

    async def test_sources_scoped_and_zero_source_refresh(self) -> None:
        """Выбор ограничен SKU и владельцем; после расхода явный ID возвращает нулевую позицию для сверки."""
        document = await self.issue_document("100")
        response = await self.client.get(
            f"{self.issues}/{document['id']}/source-positions",
            params={"document_line_id": document["lines"][0]["id"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 1)
        result = await self.issue(document, [self.actual(document, "100")])
        self.assertEqual(result.status_code, 201, result.text)
        params = {"document_line_id": document["lines"][0]["id"]}
        self.assertEqual(
            (
                await self.client.get(
                    f"{self.issues}/{document['id']}/source-positions", params=params
                )
            ).json()["total"],
            0,
        )
        refreshed = await self.client.get(
            f"{self.issues}/{document['id']}/source-positions",
            params={**params, "position_id": self.position_id},
        )
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        self.assertEqual(
            Decimal(refreshed.json()["items"][0]["on_hand_quantity"]), Decimal("0")
        )

    async def test_two_plan_lines_share_one_source_limit(self) -> None:
        """Свободный лимит каждой строки не разрешает суммарный расход позиции сверх её количества."""
        response = await self.client.post(
            self.issues,
            headers={**self.headers, "Idempotency-Key": str(uuid4())},
            json={
                "warehouse_id": self.warehouse["id"],
                "owner_id": self.company["id"],
                "lines": [
                    {
                        "inventory_item_id": self.item["id"],
                        "quantity": "100",
                        "uom": "KG",
                    }
                ]
                * 2,
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        document = response.json()
        response = await self.client.post(
            f"{self.issues}/{document['id']}/confirm",
            headers=self.headers,
            json={"expected_version": document["version"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        document = response.json()
        rows = [self.actual(document, "60"), self.actual(document, "60")]
        rows[1]["document_line_id"] = document["lines"][1]["id"]
        result = await self.issue(document, rows)
        self.assertEqual(result.status_code, 409, result.text)
        self.assertEqual(
            Decimal(result.json()["detail"]["requested_quantity"]), Decimal("120")
        )
        self.assertEqual(
            (await self.client.get(f"{self.issues}/{document['id']}")).json(), document
        )

    async def test_expired_damaged_lot_is_physical_issue_with_exact_unit_conversion(
        self,
    ) -> None:
        """Коммерческая непригодность и просрочка не заменяют физическую достаточность расхода."""
        response = await self.client.post(
            self.root + "/items",
            headers=self.headers,
            json={
                "sku": "EXPIRED-PHYSICAL",
                "base_uom": "KG",
                "tracking_mode": "LOT",
                "expiration_mode": "REQUIRED",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        item = response.json()
        response = await self.client.post(
            f"{self.root}/items/{item['id']}/lots",
            headers=self.headers,
            json={"number": "000Lot-Expired", "expires_on": "2020-01-01"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        lot = response.json()
        receipt = await self.confirmed(item, "10")
        row = self.row(receipt, "10", lot_id=lot["id"], stock_status="DAMAGED")
        received = await self.receive(receipt, [row])
        self.assertEqual(received.status_code, 201, received.text)
        position = received.json()["positions"][0]["id"]
        document = await self.issue_document("3", item=item)
        sources = await self.client.get(
            f"{self.issues}/{document['id']}/source-positions",
            params={
                "document_line_id": document["lines"][0]["id"],
                "search": "000Lot-",
            },
        )
        self.assertEqual(sources.status_code, 200, sources.text)
        self.assertEqual(sources.json()["total"], 1)
        self.assertEqual(sources.json()["items"][0]["stock_status"], "DAMAGED")
        rows = [
            self.actual(document, "1000", position),
            self.actual(document, "2", position),
        ]
        rows[0]["uom"] = "G"
        result = await self.issue(document, rows)
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(len(result.json()["ledger"]), 1)
        self.assertEqual(
            Decimal(result.json()["ledger"][0]["quantity_delta"]), Decimal("-3")
        )
        self.assertEqual(
            Decimal(result.json()["positions"][0]["after_quantity"]), Decimal("7")
        )
        self.assertEqual(result.json()["lines"][0]["lot_number"], "000Lot-Expired")
        read = await self.client.get(
            f"{self.root}/stock-executions/{result.json()['execution_id']}/issue-result"
        )
        self.assertEqual(read.status_code, 200, read.text)
        self.assertEqual(read.json(), result.json())

    async def test_lot_and_serial_partial_issue_and_receipt_after_zero(self) -> None:
        """SERIAL расходуется 1→0, даты приходят из LOT; после нуля приёмка экземпляра снова допустима."""
        response = await self.client.post(
            self.root + "/items",
            headers=self.headers,
            json={
                "sku": "SERIAL-ISSUE",
                "tracking_mode": "LOT_AND_SERIAL",
                "expiration_mode": "REQUIRED",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        item = response.json()
        response = await self.client.post(
            f"{self.root}/items/{item['id']}/lots",
            headers=self.headers,
            json={"number": "000Lot-S", "expires_on": "2028-01-01"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        lot = response.json()
        serials = []
        for number in ("000Sn-a", "000Sn-B"):
            response = await self.client.post(
                f"{self.root}/items/{item['id']}/serials",
                headers=self.headers,
                json={"number": number, "lot_id": lot["id"]},
            )
            self.assertEqual(response.status_code, 201, response.text)
            serials.append(response.json())
        receipt = await self.confirmed(item, "2")
        result = await self.receive(
            receipt,
            [
                self.row(receipt, "1", lot_id=lot["id"], serial_id=value["id"])
                for value in serials
            ],
        )
        self.assertEqual(result.status_code, 201, result.text)
        sources = {
            line["serial_id"]: line["position_id"] for line in result.json()["lines"]
        }
        document = await self.issue_document("2", item=item)
        for index, serial in enumerate(serials):
            result = await self.issue(
                document, [self.actual(document, "1", sources[serial["id"]])]
            )
            self.assertEqual(result.status_code, 201, result.text)
            self.assertEqual(
                Decimal(result.json()["positions"][0]["after_quantity"]), Decimal("0")
            )
            document = (await self.client.get(f"{self.issues}/{document['id']}")).json()
            self.assertEqual(
                document["status"], "COMPLETED" if index else "PARTIALLY_EXECUTED"
            )
        receipt = await self.confirmed(item, "1")
        result = await self.receive(
            receipt,
            [self.row(receipt, "1", lot_id=lot["id"], serial_id=serials[0]["id"])],
        )
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(
            Decimal(result.json()["positions"][0]["after_quantity"]), Decimal("1")
        )

    async def test_failure_after_outbox_rolls_back_issue_and_key(self) -> None:
        """Технический отказ в конце сценария не оставляет Ledger, прогресс или уменьшение запаса."""
        from unittest.mock import patch
        from src.modules.inventory.infrastructure.stock_document.persistence.issue_requests import (
            SqlAlchemyIssuePostingRequests,
        )

        document = await self.issue_document("10")
        rows = [self.actual(document, "10")]
        key = str(uuid4())

        async def fail(*args: object, **kwargs: object) -> None:
            """Эмулирует отказ после записи Outbox перед завершением результата команды."""
            raise RuntimeError("complete failed")

        before = await self.counts()
        with patch.object(SqlAlchemyIssuePostingRequests, "complete", fail):
            response = await self.issue(document, rows, key)
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(await self.counts(), before)
        self.assertEqual(
            (await self.client.get(f"{self.issues}/{document['id']}")).json(), document
        )
        response = await self.issue(document, rows, key)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(
            Decimal(response.json()["positions"][0]["after_quantity"]), Decimal("90")
        )

    async def test_issue_draft_edit_cancel_and_creation_replay(self) -> None:
        """Создание идемпотентно, строки исправляются только в черновике, отмена не меняет остаток."""
        key = str(uuid4())
        payload = {
            "warehouse_id": self.warehouse["id"],
            "owner_id": self.company["id"],
            "lines": [],
        }
        response = await self.client.post(
            self.issues, headers={**self.headers, "Idempotency-Key": key}, json=payload
        )
        self.assertEqual(response.status_code, 201, response.text)
        original = response.json()
        patched = await self.client.patch(
            f"{self.issues}/{original['id']}",
            headers=self.headers,
            json={
                "expected_version": original["version"],
                "lines": [
                    {"inventory_item_id": self.item["id"], "quantity": "5", "uom": "KG"}
                ],
            },
        )
        self.assertEqual(patched.status_code, 200, patched.text)
        document = patched.json()
        confirmed = await self.client.post(
            f"{self.issues}/{document['id']}/confirm",
            headers=self.headers,
            json={"expected_version": document["version"]},
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        document = confirmed.json()
        cancelled = await self.client.post(
            f"{self.issues}/{document['id']}/cancel",
            headers=self.headers,
            json={"expected_version": document["version"]},
        )
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(cancelled.json()["status"], "CANCELLED")
        replay = await self.client.post(
            self.issues, headers={**self.headers, "Idempotency-Key": key}, json=payload
        )
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(replay.json(), original)
        executed = await self.issue(
            cancelled.json(), [self.actual(cancelled.json(), "1")]
        )
        self.assertEqual(executed.status_code, 409, executed.text)

    async def test_wrong_sku_and_unknown_source_are_rejected(self) -> None:
        """ID источника не позволяет использовать запас другого SKU или несуществующую позицию."""
        response = await self.client.post(
            self.root + "/items",
            headers=self.headers,
            json={"sku": "OTHER-SKU", "base_uom": "KG"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        document = await self.issue_document("1", item=response.json())
        wrong = await self.issue(document, [self.actual(document, "1")])
        self.assertEqual(wrong.status_code, 422, wrong.text)
        missing = await self.issue(document, [self.actual(document, "1", str(uuid4()))])
        self.assertEqual(missing.status_code, 404, missing.text)
        sources = await self.client.get(
            f"{self.issues}/{document['id']}/source-positions",
            params={"document_line_id": document["lines"][0]["id"]},
        )
        self.assertEqual(sources.status_code, 200, sources.text)
        self.assertEqual(sources.json()["total"], 0)

    async def test_same_document_version_conflict_and_plan_overrun(self) -> None:
        """Версия защищает один план; лимит строки проверяется отдельно от физического количества."""
        document = await self.issue_document("20")
        responses = await asyncio.gather(
            *(self.issue(document, [self.actual(document, "10")]) for _ in range(2))
        )
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [201, 409],
            [r.text for r in responses],
        )
        conflict = next(r for r in responses if r.status_code == 409).json()["detail"]
        self.assertEqual(conflict["code"], "stock_document_version_conflict")
        current = (await self.client.get(f"{self.issues}/{document['id']}")).json()
        exceeded = await self.issue(current, [self.actual(current, "11")])
        self.assertEqual(exceeded.status_code, 422, exceeded.text)
        self.assertEqual(
            exceeded.json()["detail"]["code"], "stock_document_line_over_execution"
        )
        self.assertEqual(
            Decimal(
                (await self.read("/stock-positions/" + self.position_id))["on_hand_qty"]
            ),
            Decimal("90"),
        )

    async def test_source_query_accepts_url_pagination_and_literal_search(self) -> None:
        """URL-параметры страницы преобразуются в числа; LIKE-символы остаются буквальными."""
        document = await self.issue_document("10")
        path = f"{self.issues}/{document['id']}/source-positions"
        params = {
            "document_line_id": document["lines"][0]["id"],
            "offset": "0",
            "limit": "1",
        }
        response = await self.client.get(path, params=params)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            (response.json()["total"], len(response.json()["items"])), (1, 1)
        )
        next_page = await self.client.get(path, params={**params, "offset": "1"})
        self.assertEqual(next_page.status_code, 200, next_page.text)
        self.assertEqual(
            (next_page.json()["total"], next_page.json()["items"]), (1, [])
        )
        literal = await self.client.get(path, params={**params, "search": "%"})
        self.assertEqual(literal.status_code, 200, literal.text)
        self.assertEqual(literal.json()["total"], 0)
