"""Ручной STATUS_CHANGE: реальный tenant-UoW, исходные позиции и отрицательный Ledger."""

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
class StockStatusChangePostgresTests(unittest.IsolatedAsyncioTestCase):
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
        self.status_changes = self.root + "/stock-documents/status-changes"
        document = await self.confirmed(quantity="100")
        response = await self.receive(document, [self.row(document, "100")])
        self.assertEqual(response.status_code, 201, response.text)
        self.position_id = response.json()["positions"][0]["id"]

    async def status_change_document(
        self,
        quantity: str = "80",
        *,
        item: dict | None = None,
        target: str = "QUARANTINE",
    ) -> dict:
        """Создаёт и подтверждает независимый план STATUS_CHANGE."""
        item = item or self.item
        response = await self.client.post(
            self.status_changes,
            headers={**self.headers, "Idempotency-Key": str(uuid4())},
            json={
                "warehouse_id": self.warehouse["id"],
                "owner_id": self.company["id"],
                "reason": "Проверка качества",
                "target_status": target,
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
        self.assertEqual(document["operation_type"], "STATUS_CHANGE")
        confirmed = await self.client.post(
            f"{self.status_changes}/{document['id']}/confirm",
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

    async def status_change(
        self, document: dict, rows: list[dict], key: str | None = None
    ) -> Response:
        """Отправляет один атомарный факт с обязательным ключом."""
        return await self.client.post(
            f"{self.status_changes}/{document['id']}/change-status",
            headers={**self.headers, "Idempotency-Key": key or str(uuid4())},
            json={"expected_version": document["version"], "lines": rows},
        )

    async def test_preview_and_partial_posting(self) -> None:
        """Preview не создаёт факт; две операции сохраняют общий запас и историю."""
        document = await self.status_change_document()
        rows = [self.actual(document, "30")]
        before = await self.counts()
        preview = await self.client.post(
            f"{self.status_changes}/{document['id']}/preview",
            headers=self.headers,
            json={"expected_version": document["version"], "lines": rows},
        )
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(await self.counts(), before)
        self.assertEqual(len(preview.json()["positions"]), 2)
        result = await self.status_change(document, rows)
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(result.json()["target_status"], "QUARANTINE")
        self.assertEqual(
            sorted(Decimal(v["quantity_delta"]) for v in result.json()["ledger"]),
            [Decimal(-30), Decimal(30)],
        )
        document = (
            await self.client.get(f"{self.status_changes}/{document['id']}")
        ).json()
        result = await self.status_change(document, [self.actual(document, "50")])
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(result.json()["document_status"], "COMPLETED")
        positions = await self.read(
            "/stock-positions", inventory_item_id=self.item["id"]
        )
        self.assertEqual(
            sum(Decimal(v["on_hand_qty"]) for v in positions["items"]), Decimal(100)
        )
        journal = await self.read("/stock-movements", document_id=document["id"])
        self.assertEqual(journal["total"], 4)
        self.assertEqual(
            {v["operation_reason"] for v in journal["items"]}, {"Проверка качества"}
        )

    async def test_all_twelve_transitions_and_same_state_rejected(self) -> None:
        """Все 12 направлений разрешены; нулевой переход не создаёт факт."""
        transitions = await self.client.get(self.status_changes + "/transitions")
        self.assertEqual(transitions.status_code, 200, transitions.text)
        self.assertEqual(
            sum(len(v["target_statuses"]) for v in transitions.json()["items"]), 12
        )
        for source in ("SELLABLE", "QUARANTINE", "DAMAGED", "BLOCKED"):
            for target in ("SELLABLE", "QUARANTINE", "DAMAGED", "BLOCKED"):
                with self.subTest(source=source, target=target):
                    receipt = await self.confirmed(quantity="1")
                    received = await self.receive(
                        receipt, [self.row(receipt, "1", stock_status=source)]
                    )
                    self.assertEqual(received.status_code, 201, received.text)
                    position = received.json()["lines"][0]["position_id"]
                    document = await self.status_change_document("1", target=target)
                    before = await self.counts()
                    result = await self.status_change(
                        document, [self.actual(document, "1", position)]
                    )
                    self.assertEqual(
                        result.status_code,
                        422 if source == target else 201,
                        result.text,
                    )
                    if source == target:
                        self.assertEqual(await self.counts(), before)
                    else:
                        line = result.json()["lines"][0]
                        self.assertEqual(
                            (line["stock_status"], line["destination_stock_status"]),
                            (source, target),
                        )
                        self.assertEqual(
                            line["location_id"], line["destination_location_id"]
                        )

    async def test_preview_absent_destination_has_no_fake_identity_and_persists_nothing(
        self,
    ) -> None:
        """Повторный preview не создаёт позиции, ключи, факты или Outbox и скрывает временный ID."""
        from sqlalchemy import select, func, event
        from src.modules.inventory.infrastructure.persistence.models.stock_document_status_change import (
            StockDocumentStatusChangeModel,
        )
        from src.modules.inventory.infrastructure.persistence.models.stock_execution_status_change import (
            StockExecutionStatusChangeModel,
        )
        from src.modules.inventory.infrastructure.persistence.models.stock_status_change_creation_request import (
            StockStatusChangeCreationRequestModel,
        )
        from src.modules.inventory.infrastructure.persistence.models.stock_status_change_posting_requests import (
            StatusChangePostingRequestModel,
        )
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
            bind_tenant_schema,
        )

        document = await self.status_change_document("5", target="BLOCKED")

        async def snapshot() -> tuple[int, ...]:
            """Считает собственные дочерние таблицы и журналы ключей без неучтённых записей."""
            async with self.engine.begin() as connection:
                await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
                counts = []
                for table in (
                    StockDocumentStatusChangeModel,
                    StockExecutionStatusChangeModel,
                    StockStatusChangeCreationRequestModel,
                    StatusChangePostingRequestModel,
                ):
                    counts.append(
                        (
                            await connection.execute(
                                select(func.count()).select_from(table)
                            )
                        ).scalar_one()
                    )
                return tuple(counts)

        own_before = await snapshot()
        # Общий счётчик покрывает позиции, факты, Ledger и публичный Outbox.
        before = await self.counts()
        statements: list[str] = []

        def capture(
            conn: object,
            cursor: object,
            statement: str,
            parameters: object,
            context: object,
            executemany: bool,
        ) -> None:
            """Сохраняет только SQL без значений для доказательства отсутствия DML и блокировок."""
            statements.append(statement.upper().lstrip())

        for _ in range(2):
            statements.clear()
            event.listen(self.engine.sync_engine, "before_cursor_execute", capture)
            try:
                response = await self.client.post(
                    f"{self.status_changes}/{document['id']}/preview",
                    headers=self.headers,
                    json={
                        "expected_version": document["version"],
                        "lines": [self.actual(document, "5")],
                    },
                )
            finally:
                event.remove(self.engine.sync_engine, "before_cursor_execute", capture)
            self.assertFalse(
                any(
                    q.startswith(("INSERT ", "UPDATE ", "DELETE "))
                    or "FOR UPDATE" in q
                    or "FOR SHARE" in q
                    for q in statements
                ),
                statements,
            )
            self.assertEqual(response.status_code, 200, response.text)
            target = next(
                p for p in response.json()["positions"] if p["role"] == "DESTINATION"
            )
            self.assertEqual((target["id"], target["exists"]), (None, False))
            self.assertEqual(Decimal(target["after_quantity"]), Decimal(5))
            self.assertEqual(await self.counts(), before)
            self.assertEqual(await snapshot(), own_before)
        self.assertEqual(
            (await self.client.get(f"{self.status_changes}/{document['id']}")).json(),
            document,
        )

    async def test_serial_zeroes_source_before_destination_and_reuses_existing_position(
        self,
    ) -> None:
        """LOT_AND_SERIAL переносится 1→0/0→1 с сохранением LOT, без дубликата глобального присутствия."""
        response = await self.client.post(
            self.root + "/items",
            headers=self.headers,
            json={
                "sku": "STATUS-000SN",
                "tracking_mode": "LOT_AND_SERIAL",
                "expiration_mode": "REQUIRED",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        item = response.json()
        response = await self.client.post(
            f"{self.root}/items/{item['id']}/lots",
            headers=self.headers,
            json={"number": "000Lot-Q", "expires_on": "2030-01-01"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        lot = response.json()
        response = await self.client.post(
            f"{self.root}/items/{item['id']}/serials",
            headers=self.headers,
            json={"number": "000Sn-a", "lot_id": lot["id"]},
        )
        self.assertEqual(response.status_code, 201, response.text)
        serial = response.json()
        receipt = await self.confirmed(item, "1")
        received = await self.receive(
            receipt, [self.row(receipt, "1", lot_id=lot["id"], serial_id=serial["id"])]
        )
        self.assertEqual(received.status_code, 201, received.text)
        position = received.json()["lines"][0]["position_id"]
        source = position
        for target in ("BLOCKED", "SELLABLE"):
            document = await self.status_change_document("1", item=item, target=target)
            result = await self.status_change(
                document, [self.actual(document, "1", source)]
            )
            self.assertEqual(result.status_code, 201, result.text)
            self.assertEqual(
                sorted(
                    Decimal(p["after_quantity"]) for p in result.json()["positions"]
                ),
                [Decimal(0), Decimal(1)],
            )
            line = result.json()["lines"][0]
            self.assertEqual(
                (line["lot_id"], line["serial_id"]), (lot["id"], serial["id"])
            )
            source = line["destination_position_id"]
        self.assertEqual(source, position)
        page = await self.read("/stock-positions", serial_id=serial["id"])
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["items"][0]["stock_status"], "SELLABLE")

    async def test_insufficient_stock_preview_and_post_rollback(self) -> None:
        """Проверка и проведение независимо запрещают 101 из 100 без создания целевого нуля."""
        document = await self.status_change_document("200")
        before = await self.counts()
        payload = {
            "expected_version": document["version"],
            "lines": [self.actual(document, "101")],
        }
        preview = await self.client.post(
            f"{self.status_changes}/{document['id']}/preview",
            headers=self.headers,
            json=payload,
        )
        self.assertEqual(preview.status_code, 409, preview.text)
        result = await self.status_change(document, payload["lines"])
        self.assertEqual(result.status_code, 409, result.text)
        self.assertEqual(result.json()["detail"]["code"], "insufficient_stock_quantity")
        self.assertEqual(await self.counts(), before)

    async def test_concurrent_same_key_and_late_replay(self) -> None:
        """Параллельный и поздний повтор создают ровно один факт с двумя записями Ledger."""
        document = await self.status_change_document("20")
        rows = [self.actual(document, "10")]
        key = str(uuid4())
        results = await asyncio.wait_for(
            asyncio.gather(
                *(self.status_change(document, rows, key) for _ in range(3))
            ),
            10,
        )
        self.assertEqual(
            [r.status_code for r in results], [201] * 3, [r.text for r in results]
        )
        self.assertEqual(len({r.json()["execution_id"] for r in results}), 1)
        current = (
            await self.client.get(f"{self.status_changes}/{document['id']}")
        ).json()
        second = await self.status_change(current, [self.actual(current, "10")])
        self.assertEqual(second.status_code, 201, second.text)
        replay = await self.status_change(document, rows, key)
        self.assertEqual(replay.json(), results[0].json())
        changed = await self.status_change(document, [self.actual(document, "1")], key)
        self.assertEqual(changed.status_code, 409, changed.text)
        history = (
            await self.client.get(f"{self.status_changes}/{document['id']}/executions")
        ).json()
        self.assertEqual(history["total"], 2)

    async def test_competing_changes_cannot_overdraw_source(self) -> None:
        """Разные состояния назначения не позволяют двум документам забрать по 70 из 100."""
        documents = [
            await self.status_change_document("70", target=target)
            for target in ("QUARANTINE", "BLOCKED")
        ]
        results = await asyncio.wait_for(
            asyncio.gather(
                *(self.status_change(d, [self.actual(d, "70")]) for d in documents)
            ),
            10,
        )
        self.assertEqual(
            sorted(r.status_code for r in results),
            [201, 409],
            [r.text for r in results],
        )
        source = await self.read("/stock-positions/" + self.position_id)
        self.assertEqual(Decimal(source["on_hand_qty"]), Decimal(30))

    async def test_preview_rechecked_after_other_operation(self) -> None:
        """Успешный preview не резервирует запас и не позволяет провести устаревшее количество."""
        first = await self.status_change_document("80")
        second = await self.status_change_document("80", target="DAMAGED")
        response = await self.client.post(
            f"{self.status_changes}/{first['id']}/preview",
            headers=self.headers,
            json={
                "expected_version": first["version"],
                "lines": [self.actual(first, "80")],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.status_change(second, [self.actual(second, "80")])
        self.assertEqual(response.status_code, 201, response.text)
        response = await self.status_change(first, [self.actual(first, "80")])
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(
            response.json()["detail"]["code"], "insufficient_stock_quantity"
        )

    async def test_immutable_snapshot_and_filters_for_both_sides(self) -> None:
        """Причина и цель факта не зависят от плана, фильтры фактов находят исходное и новое состояние."""
        from sqlalchemy import update
        from uuid import UUID
        from src.modules.inventory.infrastructure.persistence.models.stock_document_status_change import (
            StockDocumentStatusChangeModel,
        )
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
            bind_tenant_schema,
        )

        document = await self.status_change_document("5")
        response = await self.status_change(document, [self.actual(document, "5")])
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        async with self.engine.begin() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            await connection.execute(
                update(StockDocumentStatusChangeModel)
                .where(
                    StockDocumentStatusChangeModel.document_id == UUID(document["id"])
                )
                .values(reason="Изменённый план", target_status="DAMAGED")
            )
        for path in (
            f"/stock-executions/{result['execution_id']}/details",
            f"/stock-postings/{result['posting_id']}/details",
        ):
            details = await self.read(path)
            self.assertEqual(
                (details["operation_reason"], details["target_status"]),
                (document["reason"], "QUARANTINE"),
            )
            self.assertEqual(
                details["lines"][0]["destination_stock_status"], "QUARANTINE"
            )
        for state in ("SELLABLE", "QUARANTINE"):
            for kind in ("executions", "postings"):
                page = await self.read(
                    f"/stock-{kind}", operation_type="STATUS_CHANGE", stock_status=state
                )
                self.assertEqual(page["total"], 1, page)
        page = await self.read("/stock-movements", document_id=document["id"])
        self.assertEqual(
            {v["operation_reason"] for v in page["items"]}, {document["reason"]}
        )
        response = await self.client.get(
            f"{self.root}/stock-executions/{result['execution_id']}/status-change-result"
        )
        self.assertEqual(response.json(), result)

    async def test_patch_target_reason_omitted_null_and_lifecycle(self) -> None:
        """Только черновик меняет реквизиты; null запрещён, отсутствие поля сохраняет значение."""
        payload = {
            "warehouse_id": self.warehouse["id"],
            "owner_id": self.company["id"],
            "reason": "Контроль качества",
            "target_status": "BLOCKED",
            "lines": [],
        }
        response = await self.client.post(
            self.status_changes,
            headers={**self.headers, "Idempotency-Key": str(uuid4())},
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        document = response.json()
        for fields in (
            {},
            {"target_status": None},
            {"reason": None},
            {"target_status": "UNKNOWN"},
        ):
            response = await self.client.patch(
                f"{self.status_changes}/{document['id']}",
                headers=self.headers,
                json={"expected_version": document["version"], **fields},
            )
            self.assertEqual(response.status_code, 422, response.text)
        response = await self.client.patch(
            f"{self.status_changes}/{document['id']}",
            headers=self.headers,
            json={"expected_version": document["version"], "target_status": "DAMAGED"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        document = response.json()
        self.assertEqual(document["reason"], payload["reason"])
        response = await self.client.patch(
            f"{self.status_changes}/{document['id']}",
            headers=self.headers,
            json={
                "expected_version": document["version"],
                "lines": [
                    {"inventory_item_id": self.item["id"], "quantity": "5", "uom": "KG"}
                ],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        document = response.json()
        response = await self.client.post(
            f"{self.status_changes}/{document['id']}/confirm",
            headers=self.headers,
            json={"expected_version": document["version"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        document = response.json()
        response = await self.client.patch(
            f"{self.status_changes}/{document['id']}",
            headers=self.headers,
            json={"expected_version": document["version"], "target_status": "SELLABLE"},
        )
        self.assertEqual(response.status_code, 409, response.text)
        response = await self.client.post(
            f"{self.status_changes}/{document['id']}/cancel",
            headers=self.headers,
            json={"expected_version": document["version"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "CANCELLED")

    async def test_failure_after_outbox_rolls_back_both_sides_and_key(self) -> None:
        """Отказ завершения ключа откатывает обе позиции, факт, реквизиты, Ledger и Outbox."""
        from unittest.mock import patch
        from src.modules.inventory.infrastructure.stock_document.persistence.status_change_requests import (
            SqlAlchemyStatusChangePostingRequests,
        )

        document = await self.status_change_document("5")
        rows = [self.actual(document, "5")]
        key = str(uuid4())
        before = await self.counts()

        async def fail(*args: object, **kwargs: object) -> None:
            """Эмулирует технический сбой после записи общего события."""
            raise RuntimeError("complete failed")

        with patch.object(SqlAlchemyStatusChangePostingRequests, "complete", fail):
            result = await self.status_change(document, rows, key)
        self.assertEqual(result.status_code, 500, result.text)
        self.assertEqual(await self.counts(), before)
        self.assertEqual(
            (await self.client.get(f"{self.status_changes}/{document['id']}")).json(),
            document,
        )
        result = await self.status_change(document, rows, key)
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(len(result.json()["ledger"]), 2)

    async def test_actual_rejects_dimension_overrides_and_wrong_source(self) -> None:
        """Фактический контракт принимает только ID позиции; смена адреса/состояния и чужой SKU запрещены."""
        document = await self.status_change_document("5")
        for fields in (
            {"target_status": "SELLABLE"},
            {"reason": "Подмена"},
            {"destination_location_id": self.location["id"]},
            {"stock_status": "DAMAGED"},
        ):
            response = await self.status_change(
                document, [{**self.actual(document, "5"), **fields}]
            )
            self.assertEqual(response.status_code, 422, response.text)
        response = await self.status_change(
            document, [self.actual(document, "5", str(uuid4()))]
        )
        self.assertEqual(response.status_code, 404, response.text)

    async def test_status_change_and_other_debits_share_lock_order(self) -> None:
        """ISSUE, WRITE_OFF, INTERNAL_MOVE и STATUS_CHANGE не расходуют суммарно 120 из 100."""
        plans = []
        for kind in ("issues", "write-offs", "internal-moves"):
            path = f"{self.root}/stock-documents/{kind}"
            payload = {
                "warehouse_id": self.warehouse["id"],
                "owner_id": self.company["id"],
                "lines": [
                    {
                        "inventory_item_id": self.item["id"],
                        "quantity": "30",
                        "uom": "KG",
                    }
                ],
            }
            if kind == "write-offs":
                payload["reason"] = "Повреждение"
            response = await self.client.post(
                path,
                headers={**self.headers, "Idempotency-Key": str(uuid4())},
                json=payload,
            )
            self.assertEqual(response.status_code, 201, response.text)
            d = response.json()
            response = await self.client.post(
                f"{path}/{d['id']}/confirm",
                headers=self.headers,
                json={"expected_version": d["version"]},
            )
            self.assertEqual(response.status_code, 200, response.text)
            plans.append((kind, response.json()))
        destination = await self.location_for(self.warehouse["id"], "B-STATUS")

        async def post_other(kind: str, document: dict) -> Response:
            """Отправляет расход общей позиции через самостоятельный тип документа."""
            line = self.actual(document, "30")
            if kind == "internal-moves":
                line["destination_location_id"] = destination["id"]
            action = {
                "issues": "issue",
                "write-offs": "write-off",
                "internal-moves": "move",
            }[kind]
            return await self.client.post(
                f"{self.root}/stock-documents/{kind}/{document['id']}/{action}",
                headers={**self.headers, "Idempotency-Key": str(uuid4())},
                json={"expected_version": document["version"], "lines": [line]},
            )

        document = await self.status_change_document("30")
        responses = await asyncio.wait_for(
            asyncio.gather(
                self.status_change(document, [self.actual(document, "30")]),
                *(post_other(kind, d) for kind, d in plans),
            ),
            10,
        )
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [201, 201, 201, 409],
            [r.text for r in responses],
        )
        source = await self.read("/stock-positions/" + self.position_id)
        self.assertEqual(Decimal(source["on_hand_qty"]), Decimal(10))
