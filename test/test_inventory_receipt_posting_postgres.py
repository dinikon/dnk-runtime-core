"""Сквозная приёмка на PostgreSQL с реальными исполнением, Ledger, позициями и public Outbox."""

import asyncio
from decimal import Decimal
import os
import unittest
from uuid import UUID, uuid4
from unittest.mock import patch
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from src.modules.inventory.presentation.stock_location.router import (
    router as location_router,
)
from src.modules.inventory.presentation.stock_lot.router import router as lot_router
from src.modules.inventory.presentation.stock_serial.router import (
    router as serial_router,
)
from src.modules.inventory.presentation.stock_execution.router import (
    router as execution_router,
)
from src.modules.inventory.presentation.stock_posting.router import (
    router as posting_router,
)
from src.modules.inventory.infrastructure.persistence.models.stock_positions import (
    StockPositionModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
    StockExecutionModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_postings import (
    StockPostingModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_ledger_entries import (
    StockLedgerEntryModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_receipt_posting_requests import (
    ReceiptPostingRequestModel,
)
from src.modules.inventory.infrastructure.stock_document.persistence.receipt_requests import (
    SqlAlchemyReceiptPostingRequests,
)
from src.modules.shared.infrastructure.events.integration_outbox_event_model import (
    IntegrationOutboxEventModel,
)
from src.modules.reference_data.infrastructure.persistence.models.currency import (
    CurrencyModel,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from test import test_inventory_receipt_postgres as support


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class ReceiptPostingPostgresTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет реальный HTTP, внешнюю транзакцию и конкурентные запросы."""

    drop_schemas = support.InventoryReceiptPostgresTests.drop_schemas
    create_receipt = support.InventoryReceiptPostgresTests.create_receipt

    async def asyncSetUp(self) -> None:
        """Создаёт tenant и существующие справочники, а также настоящий общий Outbox."""
        await support.InventoryReceiptPostgresTests.asyncSetUp(self)
        for router in (
            location_router,
            lot_router,
            serial_router,
            execution_router,
            posting_router,
        ):
            self.app.include_router(router, prefix="/api/console")
        async with self.engine.begin() as connection:
            await connection.run_sync(
                lambda conn: IntegrationOutboxEventModel.__table__.create(
                    conn, checkfirst=True
                )
            )
            await connection.run_sync(
                lambda conn: CurrencyModel.__table__.create(conn, checkfirst=True)
            )
            await connection.execute(
                pg_insert(CurrencyModel)
                .values(
                    code="USD",
                    name="US dollar",
                    numeric_code="840",
                    minor_units=2,
                    active=True,
                )
                .on_conflict_do_update(
                    index_elements=[CurrencyModel.code], set_={"active": True}
                )
            )
        self.location = await self.location_for(self.warehouse["id"], "A1")

    async def location_for(self, warehouse_id: str, code: str) -> dict:
        """Создаёт активную физическую локацию существующим HTTP-сценарием."""
        response = await self.client.post(
            f"/api/console/inventory/warehouses/{warehouse_id}/locations",
            headers=self.headers,
            json={"code": code, "name": code, "location_type": "STORAGE"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def confirmed(
        self,
        item: dict | None = None,
        quantity: str = "2",
        warehouse_id: str | None = None,
    ) -> dict:
        """Создаёт и явно подтверждает непустой план без физического факта."""
        item = item or self.item
        document = await self.create_receipt(
            {
                "warehouse_id": warehouse_id or self.warehouse["id"],
                "owner_id": self.company["id"],
                "lines": [
                    {
                        "inventory_item_id": item["id"],
                        "quantity": quantity,
                        "uom": item["base_uom"],
                    }
                ],
            }
        )
        response = await self.client.post(
            f"{self.receipts}/{document['id']}/confirm",
            headers=self.headers,
            json={"expected_version": document["version"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def row(self, document: dict, quantity: str = "2", **kwargs: object) -> dict:
        """Создаёт стабильную строку команды с серверными ссылками из плана."""
        return dict(
            client_line_id=str(uuid4()),
            document_line_id=document["lines"][0]["id"],
            quantity=quantity,
            uom=document["lines"][0]["base_uom"],
            location_id=self.location["id"],
            **kwargs,
        )

    async def receive(
        self,
        document: dict,
        rows: list[dict],
        *,
        key: str | None = None,
        costs: list[dict] | None = None,
    ):
        """Отправляет только единый сценарий проведения с обязательным ключом."""
        return await self.client.post(
            f"{self.receipts}/{document['id']}/receive",
            headers={**self.headers, "Idempotency-Key": key or str(uuid4())},
            json={
                "expected_version": document["version"],
                "lines": rows,
                "costs": costs or [],
            },
        )

    async def counts(self) -> tuple[int, ...]:
        """Читает сохранённые факты и реальный Outbox данного tenant."""
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            counts = []
            for model in (
                StockPositionModel,
                StockExecutionModel,
                StockPostingModel,
                StockLedgerEntryModel,
                ReceiptPostingRequestModel,
            ):
                counts.append(
                    (
                        await connection.execute(
                            select(func.count()).select_from(model)
                        )
                    ).scalar_one()
                )
            counts.append(
                (
                    await connection.execute(
                        select(func.count())
                        .select_from(IntegrationOutboxEventModel)
                        .where(
                            IntegrationOutboxEventModel.tenant_id == self.tenant.uuid
                        )
                    )
                ).scalar_one()
            )
            return tuple(counts)

    async def test_receipt_grouping_costs_history_and_original_replay(self) -> None:
        """Две фактические строки дают один Ledger без потери стоимости, исходных единиц и связей."""
        doc = await self.confirmed(quantity="1.25")
        rows = [self.row(doc, "500"), self.row(doc, "750")]
        for row in rows:
            row["uom"] = "G"
        costs = [
            dict(
                amount="0.0000",
                currency="USD",
                allocations=[
                    dict(client_line_id=rows[0]["client_line_id"], amount="0")
                ],
            )
        ]
        key = str(uuid4())
        response = await self.receive(doc, rows, key=key, costs=costs)
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertEqual(result["document_status"], "COMPLETED")
        self.assertEqual(
            (len(result["lines"]), len(result["ledger"]), len(result["positions"])),
            (2, 1, 1),
        )
        self.assertEqual(
            Decimal(result["positions"][0]["after_quantity"]), Decimal("1.25")
        )
        self.assertEqual(result["lines"][0]["source_quantity"], "500")
        self.assertEqual(result["costs"][0]["amount"], "0.0000")
        self.assertEqual(len(result["costs"][0]["allocations"]), 1)
        replay = await self.receive(doc, rows, key=key, costs=costs)
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(replay.json(), result)
        self.assertEqual(await self.counts(), (1, 1, 1, 1, 1, 1))
        for path in (
            f"/api/console/inventory/stock-executions/{result['execution_id']}",
            f"/api/console/inventory/stock-postings/{result['posting_id']}",
        ):
            read = await self.client.get(path)
            self.assertEqual(read.status_code, 200, read.text)
            self.assertEqual(read.json(), result)
        history = await self.client.get(f"{self.receipts}/{doc['id']}/executions")
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(history.json()["total"], 1)
        changed = await self.receive(doc, [self.row(doc, "1")], key=key)
        self.assertEqual(changed.status_code, 409, changed.text)

    async def test_partial_receipt_accumulates_one_nullable_position(self) -> None:
        """Два проведения корректно увеличивают одну позицию и завершают оставшийся план."""
        doc = await self.confirmed()
        first = await self.receive(doc, [self.row(doc, "0.5")])
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(first.json()["document_status"], "PARTIALLY_EXECUTED")
        prepared = await self.client.get(f"{self.receipts}/{doc['id']}/receipt-context")
        self.assertEqual(prepared.status_code, 200, prepared.text)
        self.assertEqual(
            Decimal(prepared.json()["lines"][0]["remaining_quantity"]), Decimal("1.5")
        )
        current = (await self.client.get(f"{self.receipts}/{doc['id']}")).json()
        second = await self.receive(current, [self.row(current, "1.5")])
        self.assertEqual(second.status_code, 201, second.text)
        self.assertEqual(second.json()["document_status"], "COMPLETED")
        self.assertEqual(
            second.json()["positions"][0]["id"], first.json()["positions"][0]["id"]
        )
        self.assertEqual(
            Decimal(second.json()["positions"][0]["after_quantity"]), Decimal("2")
        )
        self.assertEqual(await self.counts(), (1, 2, 2, 2, 2, 2))

    async def test_concurrent_idempotent_command_and_distinct_key_version_conflict(
        self,
    ) -> None:
        """Один ключ не создаёт повторные факты, другой ключ со старым планом не проводит его второй раз."""
        doc = await self.confirmed()
        rows = [self.row(doc)]
        key = str(uuid4())
        responses = await asyncio.gather(
            *(self.receive(doc, rows, key=key) for _ in range(3))
        )
        self.assertEqual(
            [r.status_code for r in responses], [201] * 3, [r.text for r in responses]
        )
        self.assertEqual(len({r.json()["execution_id"] for r in responses}), 1)
        self.assertEqual((await self.receive(doc, rows)).status_code, 409)
        self.assertEqual(await self.counts(), (1, 1, 1, 1, 1, 1))

    async def test_failure_after_outbox_rolls_back_all_facts_and_zero_positions(
        self,
    ) -> None:
        """Отказ в завершении ключа после flush Outbox откатывает все шесть групп записей."""
        doc = await self.confirmed()
        rows = [self.row(doc)]
        key = str(uuid4())

        async def fail(*args: object, **kwargs: object) -> None:
            """Эмулирует технический отказ после всех физических записей и Outbox."""
            raise RuntimeError("complete failed")

        with patch.object(SqlAlchemyReceiptPostingRequests, "complete", fail):
            response = await self.receive(doc, rows, key=key)
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(await self.counts(), (0, 0, 0, 0, 0, 0))
        self.assertEqual(
            (await self.client.get(f"{self.receipts}/{doc['id']}")).json(), doc
        )
        self.assertEqual((await self.receive(doc, rows, key=key)).status_code, 201)

    async def test_required_lot_dates_are_checked_only_from_lot(self) -> None:
        """Неполная партия создаётся, но REQUIRED не поступает без expires_on."""
        item = (
            await self.client.post(
                "/api/console/inventory/items",
                headers=self.headers,
                json={
                    "sku": "LOT-REQUIRED",
                    "tracking_mode": "LOT",
                    "expiration_mode": "REQUIRED",
                },
            )
        ).json()
        lot_response = await self.client.post(
            f"/api/console/inventory/items/{item['id']}/lots",
            headers=self.headers,
            json={"number": "000Ab"},
        )
        self.assertEqual(lot_response.status_code, 201, lot_response.text)
        lot = lot_response.json()
        doc = await self.confirmed(item)
        response = await self.receive(doc, [self.row(doc, lot_id=lot["id"])])
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(await self.counts(), (0, 0, 0, 0, 0, 0))
        response = await self.client.patch(
            f"/api/console/inventory/items/{item['id']}/lots/{lot['id']}",
            headers=self.headers,
            json={"expires_on": "2028-01-01"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.receive(doc, [self.row(doc, lot_id=lot["id"])])
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["lines"][0]["lot_number"], "000Ab")

    async def test_serial_presence_is_global_across_documents_locations_and_statuses(
        self,
    ) -> None:
        """Один SERIAL не поступает одновременно на два склада даже с разными состояниями запаса."""
        item_response = await self.client.post(
            "/api/console/inventory/items",
            headers=self.headers,
            json={"sku": "SERIAL-001", "tracking_mode": "SERIAL"},
        )
        self.assertEqual(item_response.status_code, 201, item_response.text)
        item = item_response.json()
        serial_response = await self.client.post(
            f"/api/console/inventory/items/{item['id']}/serials",
            headers=self.headers,
            json={"number": "000Sn"},
        )
        self.assertEqual(serial_response.status_code, 201, serial_response.text)
        serial = serial_response.json()
        warehouse = (
            await self.client.post(
                "/api/console/inventory/warehouses",
                headers=self.headers,
                json={"code": "WH-2", "name": "Другой склад"},
            )
        ).json()
        location = await self.location_for(warehouse["id"], "B1")
        a = await self.confirmed(item, "1")
        b = await self.confirmed(item, "1", warehouse["id"])
        row_a = self.row(a, "1", serial_id=serial["id"])
        row_b = self.row(b, "1", serial_id=serial["id"], stock_status="QUARANTINE")
        row_b["location_id"] = location["id"]
        responses = await asyncio.gather(
            self.receive(a, [row_a]), self.receive(b, [row_b])
        )
        self.assertEqual(
            sorted(r.status_code for r in responses),
            [201, 409],
            [r.text for r in responses],
        )
        self.assertEqual(await self.counts(), (1, 1, 1, 1, 1, 1))

    async def test_lot_and_serial_guards_references_and_immutable_restore(self) -> None:
        """LOT_AND_SERIAL берёт даты партии; история защищает измерения, но не номер."""
        from sqlalchemy.ext.asyncio import AsyncSession
        from src.modules.inventory.infrastructure.stock_execution.persistence.repository import (
            SqlAlchemyStockExecutionRepository,
        )
        from src.modules.inventory.infrastructure.stock_posting.persistence.repository import (
            SqlAlchemyStockPostingRepository,
        )
        from src.modules.inventory.domain.stock_execution.value_object.identifier import (
            StockExecutionIdVO,
        )
        from src.modules.inventory.domain.stock_posting.value_object.identifier import (
            StockPostingIdVO,
        )

        item = (
            await self.client.post(
                "/api/console/inventory/items",
                headers=self.headers,
                json={
                    "sku": "BOTH",
                    "tracking_mode": "LOT_AND_SERIAL",
                    "expiration_mode": "REQUIRED",
                },
            )
        ).json()
        root = f"/api/console/inventory/items/{item['id']}"
        lot = (
            await self.client.post(
                f"{root}/lots",
                headers=self.headers,
                json={
                    "number": "000Lot-a",
                    "manufactured_on": "2026-01-01",
                    "expires_on": "2028-01-01",
                },
            )
        ).json()
        other = (
            await self.client.post(
                f"{root}/lots", headers=self.headers, json={"number": "Other"}
            )
        ).json()
        serial = (
            await self.client.post(
                f"{root}/serials",
                headers=self.headers,
                json={"number": "000Sn", "lot_id": lot["id"]},
            )
        ).json()
        document = await self.confirmed(item, "1")
        # Нельзя подменить партию экземпляра даже на партию того же SKU.
        bad = await self.receive(
            document,
            [self.row(document, "1", lot_id=other["id"], serial_id=serial["id"])],
        )
        self.assertEqual(bad.status_code, 422, bad.text)
        self.assertEqual(await self.counts(), (0, 0, 0, 0, 0, 0))
        row = self.row(document, "1", lot_id=lot["id"], serial_id=serial["id"])
        costs = [
            {
                "amount": "12.3456",
                "currency": "USD",
                "basis_kind": "EXTERNAL",
                "source_system": "invoice",
                "source_reference": "000INV",
                "allocations": [
                    {"client_line_id": row["client_line_id"], "amount": "12.3456"}
                ],
            },
            {
                "amount": "10",
                "currency": "USD",
                "source_reference": "Freight",
                "allocations": [],
            },
        ]
        response = await self.receive(document, [row], costs=costs)
        self.assertEqual(response.status_code, 201, response.text)
        fact = response.json()
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with AsyncSession(bind=connection) as session:
                execution = await SqlAlchemyStockExecutionRepository(session).get(
                    StockExecutionIdVO(UUID(fact["execution_id"]))
                )
                posting = await SqlAlchemyStockPostingRepository(session).get(
                    StockPostingIdVO(UUID(fact["posting_id"]))
                )
                self.assertIsNotNone(execution)
                self.assertIsNotNone(posting)
                self.assertEqual(
                    execution.lines[0].id.uuid, UUID(fact["lines"][0]["id"])
                )
                self.assertEqual(
                    sorted(c.total.amount for c in execution.receipt_cost_evidence),
                    [Decimal("10"), Decimal("12.3456")],
                )
                self.assertEqual(posting.entries[0].quantity_delta.value, Decimal("1"))
        for payload in ({"tracking_mode": "LOT"}, {"base_uom": "KG", "tracking_mode": "LOT"}):
            changed = await self.client.patch(root, headers=self.headers, json=payload)
            self.assertEqual(changed.status_code, 409, changed.text)
        changed = await self.client.patch(
            root, headers=self.headers, json={"sku": "RENAMED"}
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        changed = await self.client.patch(
            f"{root}/serials/{serial['id']}",
            headers=self.headers,
            json={"lot_id": other["id"]},
        )
        self.assertEqual(changed.status_code, 409, changed.text)
        changed = await self.client.patch(
            f"{root}/serials/{serial['id']}",
            headers=self.headers,
            json={"number": "000Sn-Renamed"},
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        references = await self.client.get(
            f"{self.receipts}/{document['id']}/receipt-references",
            params={"kind": "serials", "document_line_id": document["lines"][0]["id"]},
        )
        self.assertEqual(references.status_code, 200, references.text)
        self.assertEqual(references.json()["total"], 0)
        historical = await self.client.get(
            f"/api/console/inventory/stock-executions/{fact['execution_id']}"
        )
        self.assertEqual(historical.json(), fact)

    async def test_cost_validation_and_exact_large_quantity(self) -> None:
        """Неверная валюта и распределение откатываются, длинный Decimal не округляется."""
        exact = "1234567890.1234567890123456789"
        item = (
            await self.client.post(
                "/api/console/inventory/items",
                headers=self.headers,
                json={
                    "sku": "PRECISE",
                    "base_uom": "KG",
                    "quantity_rules": {"step": "0.0000000000000000001"},
                },
            )
        ).json()
        document = await self.confirmed(item, exact)
        row = self.row(document, exact)
        for cost in (
            {"amount": "1", "currency": "ZZZ"},
            {
                "amount": "2",
                "currency": "USD",
                "allocations": [
                    {"client_line_id": row["client_line_id"], "amount": "1"}
                ],
            },
            {"amount": "1000000000000000", "currency": "USD"},
            {"amount": "1", "currency": "USD", "basis_kind": "EXTERNAL"},
        ):
            result = await self.receive(document, [row], costs=[cost])
            self.assertEqual(result.status_code, 422, result.text)
            self.assertEqual(await self.counts(), (0, 0, 0, 0, 0, 0))
        result = await self.receive(document, [row])
        self.assertEqual(result.status_code, 201, result.text)
        self.assertEqual(result.json()["lines"][0]["quantity"], exact)
        self.assertEqual(result.json()["positions"][0]["after_quantity"], exact)
        self.assertEqual(result.json()["costs"], [])

    async def test_actor_independent_key_tenant_isolation_and_csrf(self) -> None:
        """Ключ принадлежит tenant, повтор другим пользователем возвращает исходный факт."""
        from dataclasses import replace

        document = await self.confirmed()
        row = self.row(document)
        key = str(uuid4())
        first = await self.receive(document, [row], key=key)
        original = self.app.state.test_context
        self.app.state.test_context = replace(
            original, principal=replace(original.principal, user_id=str(uuid4()))
        )
        try:
            replay = await self.receive(document, [row], key=key)
            self.assertEqual(replay.json(), first.json())
        finally:
            self.app.state.test_context = original
        # Повтор не зависит от нынешней активности склада.
        await self.client.patch(
            f"/api/console/inventory/warehouses/{self.warehouse['id']}",
            headers=self.headers,
            json={"is_active": False},
        )
        self.assertEqual(
            (await self.receive(document, [row], key=key)).json(), first.json()
        )
        self.app.state.test_context = replace(
            original, principal=replace(original.principal, tenant_id=str(self.other))
        )
        try:
            self.assertEqual(
                (
                    await self.client.get(
                        f"/api/console/inventory/stock-executions/{first.json()['execution_id']}"
                    )
                ).status_code,
                404,
            )
            self.assertEqual(
                (await self.receive(document, [row], key=key)).status_code, 404
            )
        finally:
            self.app.state.test_context = original
        self.assertEqual(
            (
                await self.client.post(
                    f"{self.receipts}/{document['id']}/receive", json={}
                )
            ).status_code,
            403,
        )
        self.app.state.test_context = replace(original, principal=None)
        try:
            self.assertEqual(
                (await self.receive(document, [row], key=key)).status_code, 401
            )
        finally:
            self.app.state.test_context = original
        self.assertEqual(await self.counts(), (1, 1, 1, 1, 1, 1))
