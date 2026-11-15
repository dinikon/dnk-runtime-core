"""Проверяет RETURN по исходным фактическим строкам на настоящем tenant-UoW."""

import asyncio, os, unittest
from uuid import uuid4
from decimal import Decimal
from httpx import Response
from test.test_inventory_stock_read_postgres import StockReadPostgresTests as Support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Нужна отдельная PostgreSQL БД."
)
class StockReturnPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет оба направления, лимиты основания, атомарность и независимость от Ledger-группировки."""

    drop_schemas = Support.drop_schemas
    create_receipt = Support.create_receipt
    location_for = Support.location_for
    confirmed = Support.confirmed
    row = Support.row
    receive = Support.receive
    counts = Support.counts
    read = Support.read

    async def asyncSetUp(self) -> None:
        """Создаёт исходный приход 100 KG с реальными физическими позициями."""
        await Support.asyncSetUp(self)
        self.returns = self.root + "/stock-documents/returns"
        self.receipt = await self.confirmed(quantity="100")
        response = await self.receive(self.receipt, [self.row(self.receipt, "100")])
        self.assertEqual(response.status_code, 201, response.text)
        self.receipt_fact = response.json()
        self.position_id = self.receipt_fact["lines"][0]["position_id"]

    async def plan(self, origin: dict, quantity: str = "80") -> dict:
        """Создаёт и подтверждает план по одной фактической строке конкретного исполнения."""
        response = await self.client.post(
            self.returns,
            headers={**self.headers, "Idempotency-Key": str(uuid4())},
            json={
                "origin_execution_id": origin["execution_id"],
                "reason": "Возврат по основанию",
                "lines": [
                    {
                        "origin_execution_line_id": origin["lines"][0]["id"],
                        "quantity": quantity,
                        "uom": origin["lines"][0]["base_uom"],
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        document = response.json()
        response = await self.client.post(
            f"{self.returns}/{document['id']}/confirm",
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
        incoming: bool = False,
        position_id: str | None = None,
    ) -> dict:
        """Выбирает ровно одну физическую сторону, не разрешая подменить LOT/SERIAL."""
        row = {
            "client_line_id": str(uuid4()),
            "document_line_id": document["lines"][0]["id"],
            "quantity": quantity,
            "uom": document["lines"][0]["base_uom"],
        }
        if incoming:
            row.update(location_id=self.location["id"], stock_status="QUARANTINE")
        else:
            row["source_position_id"] = position_id or self.position_id
        return row

    async def post(
        self, document: dict, rows: list[dict], key: str | None = None
    ) -> Response:
        """Проводит фактический возврат с ожидаемой версией и отдельным ключом."""
        return await self.client.post(
            f"{self.returns}/{document['id']}/return",
            headers={**self.headers, "Idempotency-Key": key or str(uuid4())},
            json={"expected_version": document["version"], "lines": rows},
        )

    async def test_supplier_partial_preview_and_source_context(self) -> None:
        """Частичный возврат поставщику уменьшает запас и общий остаток исходного факта."""
        document = await self.plan(self.receipt_fact)
        self.assertEqual(document["direction"], "TO_SUPPLIER")
        rows = [self.actual(document, "30")]
        response = await self.client.post(
            f"{self.returns}/{document['id']}/preview",
            headers=self.headers,
            json={"expected_version": document["version"], "lines": rows},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            Decimal(response.json()["positions"][0]["after_quantity"]), Decimal(70)
        )
        response = await self.post(document, rows)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(
            response.json()["origin_execution_id"], self.receipt_fact["execution_id"]
        )
        context = await self.read(
            f"/stock-executions/{self.receipt_fact['execution_id']}/return-context"
        )
        self.assertEqual(Decimal(context["lines"][0]["returned_quantity"]), Decimal(30))
        self.assertEqual(
            Decimal(context["lines"][0]["remaining_quantity"]), Decimal(70)
        )
        response = await self.client.get(
            f"{self.returns}/{document['id']}/return-context"
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            Decimal(response.json()["lines"][0]["returnable_quantity"]), Decimal(70)
        )

    async def issue_fact(self, quantity: str = "80") -> dict:
        """Создаёт настоящее исходное расходование из ранее принятого запаса."""
        path = self.root + "/stock-documents/issues"
        response = await self.client.post(
            path,
            headers={**self.headers, "Idempotency-Key": str(uuid4())},
            json={
                "warehouse_id": self.warehouse["id"],
                "owner_id": self.company["id"],
                "lines": [
                    {
                        "inventory_item_id": self.item["id"],
                        "quantity": quantity,
                        "uom": "KG",
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        document = response.json()
        response = await self.client.post(
            f"{path}/{document['id']}/confirm",
            headers=self.headers,
            json={"expected_version": document["version"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        document = response.json()
        response = await self.client.post(
            f"{path}/{document['id']}/issue",
            headers={**self.headers, "Idempotency-Key": str(uuid4())},
            json={
                "expected_version": document["version"],
                "lines": [self.actual(document, quantity)],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_from_recipient_increases_chosen_status_and_preserves_original(
        self,
    ) -> None:
        """Приёмка от получателя создаёт новый положительный факт в явно выбранном состоянии."""
        issued = await self.issue_fact()
        document = await self.plan(issued, "50")
        self.assertEqual(document["direction"], "FROM_RECIPIENT")
        before = await self.read(f"/stock-executions/{issued['execution_id']}/details")
        rows = [self.actual(document, "30", incoming=True)]
        response = await self.post(document, rows)
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertEqual(Decimal(result["ledger"][0]["quantity_delta"]), Decimal(30))
        self.assertEqual(result["lines"][0]["stock_status"], "QUARANTINE")
        self.assertEqual(
            await self.read(f"/stock-executions/{issued['execution_id']}/details"),
            before,
        )
        context = await self.read(
            f"/stock-executions/{issued['execution_id']}/return-context"
        )
        self.assertEqual(
            Decimal(context["lines"][0]["remaining_quantity"]), Decimal(50)
        )
        details = await self.read(f"/stock-executions/{result['execution_id']}/details")
        self.assertEqual(details["origin_execution_id"], issued["execution_id"])
        self.assertEqual(details["return_direction"], "FROM_RECIPIENT")
        self.assertEqual(details["operation_reason"], document["reason"])
        movements = await self.read(
            "/stock-movements", document_id=document["id"], operation_type="RETURN"
        )
        self.assertEqual(movements["total"], 1)
        self.assertEqual(
            movements["items"][0]["origin_execution_id"], issued["execution_id"]
        )

    async def test_concurrent_documents_share_origin_limit(self) -> None:
        """Два входящих возврата по 70 из исходных 80 сериализуются по одному основанию."""
        origin = await self.issue_fact()
        docs = [await self.plan(origin, "70"), await self.plan(origin, "70")]
        results = await asyncio.wait_for(
            asyncio.gather(
                *(self.post(d, [self.actual(d, "70", incoming=True)]) for d in docs)
            ),
            10,
        )
        self.assertEqual(
            sorted(r.status_code for r in results),
            [201, 409],
            [r.text for r in results],
        )
        conflict = next(r for r in results if r.status_code == 409).json()["detail"]
        self.assertEqual(conflict["code"], "stock_return_limit_exceeded")
        context = await self.read(
            f"/stock-executions/{origin['execution_id']}/return-context"
        )
        self.assertEqual(Decimal(context["lines"][0]["returned_quantity"]), Decimal(70))

    async def test_same_key_replay_and_late_return(self) -> None:
        """Повтор одной команды не увеличивает накопленный возврат даже после следующего факта."""
        origin = await self.issue_fact()
        document = await self.plan(origin, "50")
        rows = [self.actual(document, "30", incoming=True)]
        key = str(uuid4())
        results = await asyncio.gather(
            *(self.post(document, rows, key) for _ in range(3))
        )
        self.assertEqual(
            [v.status_code for v in results], [201] * 3, [v.text for v in results]
        )
        self.assertEqual(len({v.json()["execution_id"] for v in results}), 1)
        current = (await self.client.get(f"{self.returns}/{document['id']}")).json()
        second = await self.post(current, [self.actual(current, "20", incoming=True)])
        self.assertEqual(second.status_code, 201, second.text)
        self.assertEqual(
            (await self.post(document, rows, key)).json(), results[0].json()
        )
        history = await self.client.get(f"{self.returns}/{document['id']}/executions")
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(history.json()["total"], 2)
        replay = await self.client.get(
            f"{self.root}/stock-executions/{results[0].json()['execution_id']}/return-result"
        )
        self.assertEqual(replay.json(), results[0].json())

    async def test_physical_limit_independent_of_return_limit(self) -> None:
        """Невыбранный лимит поступления не даёт вернуть поставщику отсутствующее количество."""
        await self.issue_fact("90")
        document = await self.plan(self.receipt_fact, "50")
        before = await self.counts()
        response = await self.post(document, [self.actual(document, "30")])
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(
            response.json()["detail"]["code"], "insufficient_stock_quantity"
        )
        self.assertEqual(await self.counts(), before)

    async def test_two_factual_lines_grouped_in_ledger_keep_independent_limits(
        self,
    ) -> None:
        """Одна позиция и одна запись Ledger не смешивают лимиты двух фактических строк."""
        receipt = await self.confirmed(quantity="100")
        received = await self.receive(
            receipt, [self.row(receipt, "30"), self.row(receipt, "70")]
        )
        self.assertEqual(received.status_code, 201, received.text)
        origin = received.json()
        self.assertEqual(len(origin["ledger"]), 1)
        document = await self.plan(origin, "30")
        response = await self.post(document, [self.actual(document, "30")])
        self.assertEqual(response.status_code, 201, response.text)
        context = await self.read(
            f"/stock-executions/{origin['execution_id']}/return-context"
        )
        self.assertEqual(
            [Decimal(v["remaining_quantity"]) for v in context["lines"]],
            [Decimal(0), Decimal(70)],
        )
        rejected = await self.client.post(
            self.returns,
            headers={**self.headers, "Idempotency-Key": str(uuid4())},
            json={
                "origin_execution_id": origin["execution_id"],
                "reason": "Ещё возврат",
                "lines": [
                    {
                        "origin_execution_line_id": origin["lines"][0]["id"],
                        "quantity": "1",
                        "uom": "KG",
                    }
                ],
            },
        )
        self.assertEqual(rejected.status_code, 409, rejected.text)

    async def test_preview_never_writes_and_failure_rolls_back_usage(self) -> None:
        """Preview не меняет учёт; технический сбой не занимает лимит исходной строки."""
        from unittest.mock import patch
        from src.modules.inventory.infrastructure.stock_document.persistence.return_requests import (
            SqlAlchemyReturnPostingRequests,
        )

        document = await self.plan(self.receipt_fact, "10")
        rows = [self.actual(document, "10")]
        key = str(uuid4())
        before = await self.counts()
        response = await self.client.post(
            f"{self.returns}/{document['id']}/preview",
            headers=self.headers,
            json={"expected_version": document["version"], "lines": rows},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(await self.counts(), before)

        async def fail(*args: object, **kwargs: object) -> None:
            """Эмулирует отказ после записи Outbox до завершения ключа."""
            raise RuntimeError("complete failed")

        with patch.object(SqlAlchemyReturnPostingRequests, "complete", fail):
            response = await self.post(document, rows, key)
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(await self.counts(), before)
        context = await self.read(
            f"/stock-executions/{self.receipt_fact['execution_id']}/return-context"
        )
        self.assertEqual(Decimal(context["lines"][0]["returned_quantity"]), Decimal(0))
        response = await self.post(document, rows, key)
        self.assertEqual(response.status_code, 201, response.text)

    async def test_serial_identity_and_global_presence_in_both_tracking_modes(
        self,
    ) -> None:
        """Возвращается исходный экземпляр; новое положительное присутствие запрещает повторный приём."""
        for mode in ("SERIAL", "LOT_AND_SERIAL"):
            with self.subTest(mode=mode):
                response = await self.client.post(
                    self.root + "/items",
                    headers=self.headers,
                    json={
                        "sku": "RETURN-" + mode,
                        "tracking_mode": mode,
                        "expiration_mode": (
                            "REQUIRED" if mode == "LOT_AND_SERIAL" else "NONE"
                        ),
                    },
                )
                self.assertEqual(response.status_code, 201, response.text)
                item = response.json()
                lot_id = None
                if mode == "LOT_AND_SERIAL":
                    response = await self.client.post(
                        f"{self.root}/items/{item['id']}/lots",
                        headers=self.headers,
                        json={"number": "000Lot-R", "expires_on": "2028-02-03"},
                    )
                    self.assertEqual(response.status_code, 201, response.text)
                    lot_id = response.json()["id"]
                response = await self.client.post(
                    f"{self.root}/items/{item['id']}/serials",
                    headers=self.headers,
                    json={"number": "000Sn-R", "lot_id": lot_id},
                )
                self.assertEqual(response.status_code, 201, response.text)
                serial = response.json()
                receipt = await self.confirmed(item, "1")
                received = await self.receive(
                    receipt,
                    [self.row(receipt, "1", lot_id=lot_id, serial_id=serial["id"])],
                )
                self.assertEqual(received.status_code, 201, received.text)
                source = received.json()["lines"][0]["position_id"]
                issue_path = self.root + "/stock-documents/issues"
                response = await self.client.post(
                    issue_path,
                    headers={**self.headers, "Idempotency-Key": str(uuid4())},
                    json={
                        "warehouse_id": self.warehouse["id"],
                        "owner_id": self.company["id"],
                        "lines": [
                            {
                                "inventory_item_id": item["id"],
                                "quantity": "1",
                                "uom": "PCS",
                            }
                        ],
                    },
                )
                self.assertEqual(response.status_code, 201, response.text)
                issue = response.json()
                response = await self.client.post(
                    f"{issue_path}/{issue['id']}/confirm",
                    headers=self.headers,
                    json={"expected_version": issue["version"]},
                )
                self.assertEqual(response.status_code, 200, response.text)
                issue = response.json()
                response = await self.client.post(
                    f"{issue_path}/{issue['id']}/issue",
                    headers={**self.headers, "Idempotency-Key": str(uuid4())},
                    json={
                        "expected_version": issue["version"],
                        "lines": [self.actual(issue, "1", position_id=source)],
                    },
                )
                self.assertEqual(response.status_code, 201, response.text)
                origin = response.json()
                document = await self.plan(origin, "1")
                competing = await self.plan(origin, "1")
                # Ordinary new receipt proves presence is independent of the original return budget.
                receipt = await self.confirmed(item, "1")
                received = await self.receive(
                    receipt,
                    [self.row(receipt, "1", lot_id=lot_id, serial_id=serial["id"])],
                )
                self.assertEqual(received.status_code, 201, received.text)
                before = await self.counts()
                rejected = await self.post(
                    document, [self.actual(document, "1", incoming=True)]
                )
                self.assertEqual(rejected.status_code, 422, rejected.text)
                self.assertEqual(await self.counts(), before)
                supplier_return = await self.plan(received.json(), "1")
                response = await self.post(
                    supplier_return,
                    [self.actual(supplier_return, "1", position_id=source)],
                )
                self.assertEqual(response.status_code, 201, response.text)
                response = await self.post(
                    document, [self.actual(document, "1", incoming=True)]
                )
                self.assertEqual(response.status_code, 201, response.text)
                self.assertEqual(response.json()["lines"][0]["serial_id"], serial["id"])
                self.assertEqual(response.json()["lines"][0]["lot_id"], lot_id)
                response = await self.post(
                    competing, [self.actual(competing, "1", incoming=True)]
                )
                self.assertEqual(response.status_code, 409, response.text)

    async def test_lot_identity_current_required_dates_and_unit_conversion(
        self,
    ) -> None:
        """Приходящий возврат использует текущие даты исходной LOT и не допускает подмену другой партией."""
        response = await self.client.post(
            self.root + "/items",
            headers=self.headers,
            json={
                "sku": "RETURN-LOT",
                "base_uom": "KG",
                "tracking_mode": "LOT",
                "expiration_mode": "OPTIONAL",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        item = response.json()
        response = await self.client.post(
            f"{self.root}/items/{item['id']}/lots",
            headers=self.headers,
            json={"number": "000Lot-NoDates"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        lot = response.json()
        receipt = await self.confirmed(item, "10")
        received = await self.receive(
            receipt, [self.row(receipt, "10", lot_id=lot["id"])]
        )
        self.assertEqual(received.status_code, 201, received.text)
        supplier = await self.plan(received.json(), "2")
        row = self.actual(
            supplier, "1000", position_id=received.json()["lines"][0]["position_id"]
        )
        row["uom"] = "G"
        result = await self.post(supplier, [row])
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(
            Decimal(result.json()["ledger"][0]["quantity_delta"]), Decimal("-1")
        )
        # Current source identity, not merely the SKU, also restricts source searches.
        response = await self.client.post(
            f"{self.root}/items/{item['id']}/lots",
            headers=self.headers,
            json={"number": "OTHER"},
        )
        other = response.json()
        receipt2 = await self.confirmed(item, "10")
        other_received = await self.receive(
            receipt2, [self.row(receipt2, "10", lot_id=other["id"])]
        )
        self.assertEqual(other_received.status_code, 201, other_received.text)
        rejected = await self.post(
            supplier,
            [
                self.actual(
                    supplier,
                    "1",
                    position_id=other_received.json()["lines"][0]["position_id"],
                )
            ],
        )
        self.assertEqual(
            rejected.status_code, 409, rejected.text
        )  # stale version first
        supplier = (await self.client.get(f"{self.returns}/{supplier['id']}")).json()
        rejected = await self.post(
            supplier,
            [
                self.actual(
                    supplier,
                    "1",
                    position_id=other_received.json()["lines"][0]["position_id"],
                )
            ],
        )
        self.assertEqual(rejected.status_code, 422, rejected.text)
        source_query = await self.client.get(
            f"{self.returns}/{supplier['id']}/source-positions",
            params={"document_line_id": supplier["lines"][0]["id"]},
        )
        self.assertEqual(source_query.status_code, 200, source_query.text)
        self.assertEqual(
            {v["lot_id"] for v in source_query.json()["items"]}, {lot["id"]}
        )

    async def test_draft_edit_cancel_immutable_origin_and_contracts(self) -> None:
        """Черновик сохраняет исходную строку, версия защищает редактор, подтверждение фиксирует основание."""
        payload = {
            "origin_execution_id": self.receipt_fact["execution_id"],
            "reason": "Начальная причина",
            "lines": [
                {
                    "origin_execution_line_id": self.receipt_fact["lines"][0]["id"],
                    "quantity": "10",
                    "uom": "KG",
                }
            ],
        }
        key = str(uuid4())
        headers = {**self.headers, "Idempotency-Key": key}
        response = await self.client.post(self.returns, headers=headers, json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        document = response.json()
        self.assertEqual(
            (
                await self.client.post(self.returns, headers=headers, json=payload)
            ).json(),
            document,
        )
        response = await self.client.post(
            self.returns, headers=headers, json={**payload, "reason": "Другой запрос"}
        )
        self.assertEqual(response.status_code, 409, response.text)
        url = f"{self.returns}/{document['id']}"
        patch = {
            "expected_version": document["version"],
            "reason": "Изменённая причина",
            "lines": [
                {"id": document["lines"][0]["id"], "quantity": "12", "uom": "KG"}
            ],
        }
        response = await self.client.patch(url, headers=self.headers, json=patch)
        self.assertEqual(response.status_code, 200, response.text)
        edited = response.json()
        self.assertEqual(edited["lines"][0]["id"], document["lines"][0]["id"])
        self.assertEqual(
            edited["lines"][0]["origin_execution_line_id"],
            payload["lines"][0]["origin_execution_line_id"],
        )
        response = await self.client.patch(url, headers=self.headers, json=patch)
        self.assertEqual(response.status_code, 409, response.text)
        for invalid in (
            {"reason": None},
            {"origin_execution_id": str(uuid4())},
            {"direction": "FROM_RECIPIENT"},
        ):
            response = await self.client.patch(
                url,
                headers=self.headers,
                json={"expected_version": edited["version"], **invalid},
            )
            self.assertEqual(response.status_code, 422, response.text)
        response = await self.client.post(
            url + "/confirm",
            headers=self.headers,
            json={"expected_version": edited["version"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        confirmed = response.json()
        response = await self.client.patch(
            url,
            headers=self.headers,
            json={"expected_version": confirmed["version"], "reason": "Нельзя"},
        )
        self.assertEqual(response.status_code, 409, response.text)
        response = await self.client.post(
            url + "/cancel",
            headers=self.headers,
            json={"expected_version": confirmed["version"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "CANCELLED")
        context = await self.read(
            f"/stock-executions/{self.receipt_fact['execution_id']}/return-context"
        )
        self.assertEqual(Decimal(context["lines"][0]["returned_quantity"]), Decimal(0))

    async def test_preview_incoming_has_no_dml_locks_or_new_identity(self) -> None:
        """Обычное чтение preview не создаёт даже нулевую позицию или ключ команды."""
        from sqlalchemy import event

        origin = await self.issue_fact()
        document = await self.plan(origin, "10")
        statements = []

        def capture(
            conn: object,
            cursor: object,
            statement: str,
            parameters: object,
            context: object,
            executemany: bool,
        ) -> None:
            """Сохраняет только SQL без параметров."""
            statements.append(statement.upper().lstrip())

        event.listen(self.engine.sync_engine, "before_cursor_execute", capture)
        try:
            response = await self.client.post(
                f"{self.returns}/{document['id']}/preview",
                headers=self.headers,
                json={
                    "expected_version": document["version"],
                    "lines": [self.actual(document, "10", incoming=True)],
                },
            )
        finally:
            event.remove(self.engine.sync_engine, "before_cursor_execute", capture)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(
            any(
                q.startswith(("INSERT ", "UPDATE ", "DELETE "))
                or "FOR UPDATE" in q
                or "FOR SHARE" in q
                for q in statements
            ),
            statements,
        )
        self.assertEqual(
            (
                response.json()["positions"][0]["id"],
                response.json()["positions"][0]["exists"],
            ),
            (None, False),
        )

    async def test_cancel_after_fact_and_return_as_origin_forbidden(self) -> None:
        """Выполненный возврат нельзя просто отменить или использовать как новое основание возврата."""
        document = await self.plan(self.receipt_fact, "10")
        result = await self.post(document, [self.actual(document, "5")])
        self.assertEqual(result.status_code, 201, result.text)
        current = (await self.client.get(f"{self.returns}/{document['id']}")).json()
        response = await self.client.post(
            f"{self.returns}/{document['id']}/cancel",
            headers=self.headers,
            json={"expected_version": current["version"]},
        )
        self.assertEqual(response.status_code, 409, response.text)
        response = await self.client.get(
            f"{self.root}/stock-executions/{result.json()['execution_id']}/return-context"
        )
        self.assertEqual(response.status_code, 422, response.text)
        response = await self.client.get(
            self.returns,
            params={
                "origin_execution_id": self.receipt_fact["execution_id"],
                "status": "ALL",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 1)
        response = await self.post(
            current, [{**self.actual(current, "1"), "lot_id": str(uuid4())}]
        )
        self.assertEqual(response.status_code, 422, response.text)

    async def test_origin_budget_lock_compatible_with_foreign_key_readers(self) -> None:
        """Блокировка лимита не мешает FK-связям параллельно создаваемых черновиков."""
        from sqlalchemy import select
        from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
            StockExecutionModel,
        )
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
            bind_tenant_schema,
        )
        from uuid import UUID

        document = await self.plan(self.receipt_fact, "5")
        async with self.engine.begin() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            await connection.execute(
                select(StockExecutionModel.id)
                .where(
                    StockExecutionModel.id == UUID(self.receipt_fact["execution_id"])
                )
                .with_for_update(read=True, key_share=True)
            )
            response = await asyncio.wait_for(
                self.post(document, [self.actual(document, "5")]), 3
            )
            self.assertEqual(response.status_code, 201, response.text)

    async def test_recipient_return_checks_current_required_lot_dates(self) -> None:
        """Режим REQUIRED проверяется по актуальной партии при новом входящем факте."""
        response = await self.client.post(
            self.root + "/items",
            headers=self.headers,
            json={
                "sku": "RETURN-DATES",
                "base_uom": "KG",
                "tracking_mode": "LOT",
                "expiration_mode": "OPTIONAL",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        item = response.json()
        response = await self.client.post(
            f"{self.root}/items/{item['id']}/lots",
            headers=self.headers,
            json={"number": "000Lot-Dates"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        lot = response.json()
        receipt = await self.confirmed(item, "10")
        response = await self.receive(
            receipt, [self.row(receipt, "10", lot_id=lot["id"])]
        )
        self.assertEqual(response.status_code, 201, response.text)
        position = response.json()["lines"][0]["position_id"]
        path = self.root + "/stock-documents/issues"
        response = await self.client.post(
            path,
            headers={**self.headers, "Idempotency-Key": str(uuid4())},
            json={
                "warehouse_id": self.warehouse["id"],
                "owner_id": self.company["id"],
                "lines": [
                    {"inventory_item_id": item["id"], "quantity": "10", "uom": "KG"}
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        issue = response.json()
        response = await self.client.post(
            f"{path}/{issue['id']}/confirm",
            headers=self.headers,
            json={"expected_version": issue["version"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        issue = response.json()
        response = await self.client.post(
            f"{path}/{issue['id']}/issue",
            headers={**self.headers, "Idempotency-Key": str(uuid4())},
            json={
                "expected_version": issue["version"],
                "lines": [self.actual(issue, "10", position_id=position)],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        origin = response.json()
        response = await self.client.patch(
            f"{self.root}/items/{item['id']}",
            headers=self.headers,
            json={"expiration_mode": "REQUIRED"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        document = await self.plan(origin, "10")
        rows = [self.actual(document, "5", incoming=True)]
        before = await self.counts()
        key = str(uuid4())
        response = await self.post(document, rows, key)
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(await self.counts(), before)
        response = await self.client.patch(
            f"{self.root}/items/{item['id']}/lots/{lot['id']}",
            headers=self.headers,
            json={"expires_on": "2028-02-03"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.post(document, rows, key)
        self.assertEqual(response.status_code, 201, response.text)
        target = await self.read(
            "/stock-positions/" + response.json()["lines"][0]["position_id"]
        )
        self.assertEqual(target["expires_on"], "2028-02-03")

    async def test_tenant_isolation_csrf_missing_origin_and_event_basis(self) -> None:
        """RETURN не раскрывает чужие основания; событие содержит точную связь исходных строк."""
        from dataclasses import replace
        from uuid import UUID
        from sqlalchemy import select
        from src.modules.shared.infrastructure.events.integration_outbox_event_model import (
            IntegrationOutboxEventModel,
        )

        document = await self.plan(self.receipt_fact, "5")
        rows = [self.actual(document, "5")]
        key = str(uuid4())
        result = await self.post(document, rows, key)
        self.assertEqual(result.status_code, 201, result.text)
        async with self.engine.begin() as connection:
            payload = (
                await connection.execute(
                    select(IntegrationOutboxEventModel.payload).where(
                        IntegrationOutboxEventModel.id
                        == UUID(result.json()["event_id"])
                    )
                )
            ).scalar_one()
        self.assertEqual(
            payload["origin_execution_id"], self.receipt_fact["execution_id"]
        )
        self.assertEqual(
            payload["lines"][0]["origin_execution_line_id"],
            self.receipt_fact["lines"][0]["id"],
        )
        self.assertEqual(
            (
                await self.client.post(
                    f"{self.returns}/{document['id']}/return", json={}
                )
            ).status_code,
            403,
        )
        original = self.app.state.test_context
        self.app.state.test_context = replace(
            original, principal=replace(original.principal, tenant_id=str(self.other))
        )
        try:
            for path in (
                f"{self.returns}/{document['id']}",
                f"{self.root}/stock-executions/{self.receipt_fact['execution_id']}/return-context",
                f"{self.root}/stock-executions/{result.json()['execution_id']}/return-result",
            ):
                response = await self.client.get(path)
                self.assertEqual(response.status_code, 404, response.text)
            response = await self.post(document, rows, key)
            self.assertEqual(response.status_code, 404, response.text)
        finally:
            self.app.state.test_context = original
        response = await self.client.post(
            self.returns,
            headers={**self.headers, "Idempotency-Key": str(uuid4())},
            json={
                "origin_execution_id": str(uuid4()),
                "reason": "Нет основания",
                "lines": [],
            },
        )
        self.assertEqual(response.status_code, 404, response.text)
        response = await self.client.post(
            self.returns,
            headers={**self.headers, "Idempotency-Key": str(uuid4())},
            json={
                "origin_execution_id": self.receipt_fact["execution_id"],
                "direction": "FROM_RECIPIENT",
                "reason": "Подмена",
                "lines": [],
            },
        )
        self.assertEqual(response.status_code, 422, response.text)
