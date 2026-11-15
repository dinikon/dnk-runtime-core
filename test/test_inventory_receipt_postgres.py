from src.modules.inventory.infrastructure.persistence.models.stock_positions import StockPositionModel
from src.modules.inventory.infrastructure.persistence.models.stock_executions import StockExecutionModel
from src.modules.inventory.infrastructure.persistence.models.stock_postings import StockPostingModel
from src.modules.inventory.infrastructure.persistence.models.stock_ledger_entries import StockLedgerEntryModel
"""Поступления: реальный HTTP/UoW, точность, идемпотентность и защита ссылок на PostgreSQL."""

import asyncio
from dataclasses import replace
from decimal import Decimal
import os
import unittest
from unittest.mock import patch
from typing import Any
from uuid import UUID, uuid4
from sqlalchemy import select, func, inspect
from src.modules.crm.domain.company.aggregate import CompanyEntity
from src.modules.inventory.application.stock_document.port.owner_reference import (
    StockOwnerReference,
)
from src.modules.inventory.presentation.stock_document.router import (
    router as receipt_router,
)
from src.modules.inventory.presentation.warehouse.router import (
    router as warehouse_router,
)
from src.modules.inventory.presentation.inventory_item.router import (
    router as item_router,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_line import (
    StockDocumentLineModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_creation_request import (
    StockDocumentCreationRequestModel,
)
from src.modules.inventory.infrastructure.stock_document.persistence.creation_requests import (
    SqlAlchemyReceiptCreationRequests,
)
from src.modules.inventory.infrastructure.stock_document.persistence.mapper import (
    StockDocumentMapper,
)
from src.modules.inventory.infrastructure.stock_document.owner_reference import (
    CrmStockOwnerReference,
)
from src.modules.crm.infrastructure.company.persistence.repository import (
    SqlAlchemyCompanyRepository,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from test.crm_postgres_support import CrmPostgresTestCase


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class InventoryReceiptPostgresTests(unittest.IsolatedAsyncioTestCase):
    drop_schemas = CrmPostgresTestCase.drop_schemas

    async def asyncSetUp(self) -> None:
        await CrmPostgresTestCase.asyncSetUp(self)
        self.app.include_router(receipt_router, prefix="/api/console")
        self.app.include_router(warehouse_router, prefix="/api/console")
        self.app.include_router(item_router, prefix="/api/console")
        response = await self.client.post(
            "/api/console/inventory/warehouses",
            headers=self.headers,
            json={"code": "WH-1", "name": "Основной склад"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.warehouse = response.json()
        response = await self.client.post(
            "/api/console/inventory/items",
            headers=self.headers,
            json={
                "sku": "Oil-001",
                "base_uom": "KG",
                "quantity_rules": {"step": "0.0000000000000000001"},
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.item = response.json()
        self.receipts = "/api/console/inventory/stock-documents"
        self.receipt_payload = {
            "warehouse_id": self.warehouse["id"],
            "owner_id": self.company["id"],
            "lines": [
                {"inventory_item_id": self.item["id"], "quantity": "1250", "uom": "G"},
                {
                    "inventory_item_id": self.item["id"],
                    "quantity": "1234567890.1234567890123456789",
                    "uom": "KG",
                },
            ],
        }

    async def create_receipt(
        self, payload: dict[str, Any] | None = None, *, key: str | None = None
    ) -> dict[str, Any]:
        """Создаёт документ через реальный HTTP-контракт с новым или заданным ключом."""
        response = await self.client.post(
            self.receipts,
            headers={**self.headers, "Idempotency-Key": key or str(uuid4())},
            json=self.receipt_payload if payload is None else payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_create_card_duplicate_sku_exact_conversion_and_no_physical_side_effects(
        self,
    ) -> None:
        document = await self.create_receipt()
        self.assertEqual(
            (document["operation_type"], document["status"], document["version"]),
            ("RECEIPT", "DRAFT", 2),
        )
        self.assertEqual(document["owner_name"], "Supplier ACME")
        self.assertEqual(document["source_system"], None)
        self.assertEqual([r["position"] for r in document["lines"]], [0, 1])
        self.assertEqual([r["sku"] for r in document["lines"]], ["oil-001", "oil-001"])
        self.assertNotEqual(document["lines"][0]["id"], document["lines"][1]["id"])
        self.assertEqual(Decimal(document["lines"][0]["planned_qty"]), Decimal("1.25"))
        self.assertEqual(
            Decimal(document["lines"][0]["factor_to_base"]), Decimal("0.001")
        )
        self.assertEqual(
            document["lines"][1]["planned_qty"], "1234567890.1234567890123456789"
        )
        self.assertTrue(all(Decimal(r["executed_qty"]) == 0 for r in document["lines"]))
        response = await self.client.get(f"{self.receipts}/{document['id']}")
        self.assertEqual(response.json(), document)
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            for model in (StockPositionModel, StockExecutionModel, StockPostingModel, StockLedgerEntryModel):
                self.assertEqual((await connection.execute(select(func.count()).select_from(model))).scalar_one(), 0)
            async with self.sessions(bind=connection) as session:
                model = (await session.scalars(select(StockDocumentModel))).one()
                lines = (
                    await session.scalars(
                        select(StockDocumentLineModel).order_by(
                            StockDocumentLineModel.position
                        )
                    )
                ).all()
                restored = StockDocumentMapper.to_domain(model, lines)
                self.assertEqual((restored.version, len(restored.lines)), (2, 2))
                self.assertEqual(
                    StockDocumentMapper.to_line_insert_values(restored)[1][
                        "planned_qty"
                    ],
                    Decimal("1234567890.1234567890123456789"),
                )

    async def test_empty_draft_version_zero(self) -> None:
        payload = {k: v for k, v in self.receipt_payload.items() if k != "lines"}
        document = await self.create_receipt(payload)
        self.assertEqual((document["version"], document["lines"]), (0, []))
        self.assertEqual(
            (await self.client.get(f"{self.receipts}/{document['id']}")).json(),
            document,
        )

    async def test_idempotency_replay_normalization_and_conflicting_payload(
        self,
    ) -> None:
        key = str(uuid4())
        first = await self.create_receipt(key=key)
        payload = {
            **self.receipt_payload,
            "lines": [dict(l) for l in self.receipt_payload["lines"]],
        }
        payload["lines"][0]["quantity"] = "1250.000"
        payload["lines"][0]["uom"] = "g"
        self.assertEqual(await self.create_receipt(payload, key=key), first)
        response = await self.client.post(
            self.receipts,
            headers={**self.headers, "Idempotency-Key": key},
            json={**self.receipt_payload, "lines": []},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual((await self.client.get(self.receipts)).json()["total"], 1)

    async def test_replay_returns_original_snapshot_after_reference_changes(
        self,
    ) -> None:
        key = str(uuid4())
        first = await self.create_receipt(key=key)
        response = await self.client.patch(
            f"/api/console/inventory/items/{self.item['id']}",
            headers=self.headers,
            json={"sku": "renamed"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.client.patch(
            f"/api/console/inventory/warehouses/{self.warehouse['id']}",
            headers=self.headers,
            json={"is_active": False, "name": "Другой склад"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.client.patch(
            f"/api/console/crm/companies/{self.company['id']}",
            headers=self.headers,
            json={"legal_name": "Новое имя владельца"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(await self.create_receipt(key=key), first)
        card = (await self.client.get(f"{self.receipts}/{first['id']}")).json()
        self.assertEqual(card["owner_name"], "Новое имя владельца")
        self.assertEqual(card["warehouse_name"], "Другой склад")
        self.assertEqual(card["lines"], first["lines"])

    async def test_concurrent_same_key_creates_one_document(self) -> None:
        key = str(uuid4())
        responses = await asyncio.gather(
            *(
                self.client.post(
                    self.receipts,
                    headers={**self.headers, "Idempotency-Key": key},
                    json=self.receipt_payload,
                )
                for _ in range(3)
            )
        )
        self.assertEqual(
            [r.status_code for r in responses], [201] * 3, [r.text for r in responses]
        )
        self.assertEqual(responses[0].json(), responses[1].json())
        self.assertEqual(responses[1].json(), responses[2].json())
        self.assertEqual((await self.client.get(self.receipts)).json()["total"], 1)

    async def test_failed_creation_rolls_back_document_lines_and_claim(self) -> None:
        key = str(uuid4())

        async def fail(*args: Any, **kwargs: Any) -> None:
            """Эмулирует технический отказ после записи документа до общего commit."""
            raise RuntimeError("storage failed before commit")

        with patch.object(SqlAlchemyReceiptCreationRequests, "complete", fail):
            response = await self.client.post(
                self.receipts,
                headers={**self.headers, "Idempotency-Key": key},
                json=self.receipt_payload,
            )
            self.assertEqual(response.status_code, 500, response.text)
        async with self.engine.connect() as connection:
            await bind_tenant_schema(connection, self.tenant.uuid, self.naming)
            async with self.sessions(bind=connection) as session:
                for model in (
                    StockDocumentModel,
                    StockDocumentLineModel,
                    StockDocumentCreationRequestModel,
                ):
                    self.assertEqual(
                        await session.scalar(select(func.count()).select_from(model)), 0
                    )
        await self.create_receipt(key=key)

    async def test_invalid_lines_and_missing_references_do_not_leave_claims(
        self,
    ) -> None:
        for line in (
            {"inventory_item_id": self.item["id"], "quantity": "0", "uom": "KG"},
            {"inventory_item_id": self.item["id"], "quantity": "-1", "uom": "KG"},
            {"inventory_item_id": self.item["id"], "quantity": "1", "uom": "M"},
            {"inventory_item_id": self.item["id"], "quantity": 1, "uom": "KG"},
            {"inventory_item_id": self.item["id"], "quantity": "NaN", "uom": "KG"},
        ):
            response = await self.client.post(
                self.receipts,
                headers={**self.headers, "Idempotency-Key": str(uuid4())},
                json={**self.receipt_payload, "lines": [line]},
            )
            self.assertEqual(response.status_code, 422, response.text)
        for values in (
            {"owner_id": str(uuid4())},
            {"warehouse_id": str(uuid4())},
            {
                "lines": [
                    {"inventory_item_id": str(uuid4()), "quantity": "1", "uom": "KG"}
                ]
            },
        ):
            response = await self.client.post(
                self.receipts,
                headers={**self.headers, "Idempotency-Key": str(uuid4())},
                json={**self.receipt_payload, **values},
            )
            self.assertEqual(response.status_code, 404, response.text)
        for values in (
            {"status": "CONFIRMED"},
            {"operation_type": "ISSUE"},
            {"version": 0},
            {"lines": None},
        ):
            response = await self.client.post(
                self.receipts,
                headers={**self.headers, "Idempotency-Key": str(uuid4())},
                json={**self.receipt_payload, **values},
            )
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual((await self.client.get(self.receipts)).json()["total"], 0)

    async def test_inactive_warehouse_is_rejected(self) -> None:
        await self.client.patch(
            f"/api/console/inventory/warehouses/{self.warehouse['id']}",
            headers=self.headers,
            json={"is_active": False},
        )
        response = await self.client.post(
            self.receipts,
            headers={**self.headers, "Idempotency-Key": str(uuid4())},
            json=self.receipt_payload,
        )
        self.assertEqual(response.status_code, 422, response.text)

    async def test_list_search_filters_count_and_pagination(self) -> None:
        first = await self.create_receipt()
        empty = await self.create_receipt({**self.receipt_payload, "lines": []})
        page = (
            await self.client.get(
                self.receipts,
                params={
                    "search": "OIL-001",
                    "warehouse_id": self.warehouse["id"],
                    "owner_id": self.company["id"],
                    "created_from": first["created_at"],
                    "created_to": empty["created_at"],
                },
            )
        ).json()
        self.assertEqual(
            (page["total"], len(page["items"]), page["items"][0]["line_count"]),
            (1, 1, 2),
        )
        page = (
            await self.client.get(self.receipts, params={"limit": 1, "offset": 1})
        ).json()
        self.assertEqual((page["total"], page["items"][0]["id"]), (2, first["id"]))
        self.assertEqual(
            (await self.client.get(self.receipts, params={"search": "_%"})).json()[
                "total"
            ],
            0,
        )
        for query in (
            {"created_from": "2026-11-15T00:00:00"},
            {
                "created_from": "2026-11-16T00:00:00Z",
                "created_to": "2026-11-15T00:00:00Z",
            },
            {"limit": 101},
        ):
            self.assertEqual(
                (await self.client.get(self.receipts, params=query)).status_code, 422
            )

    async def test_used_owner_and_sku_cannot_be_deleted(self) -> None:
        await self.create_receipt()
        for path in (
            f"/api/console/crm/companies/{self.company['id']}",
            f"/api/console/inventory/items/{self.item['id']}",
        ):
            response = await self.client.delete(path, headers=self.headers)
            self.assertEqual(response.status_code, 409, response.text)

    async def test_owner_namespace_does_not_fall_back_to_contact(self) -> None:
        response = await self.client.post(
            "/api/console/crm/contacts",
            headers=self.headers,
            json={"first_name": "Частное лицо"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        response = await self.client.post(
            self.receipts,
            headers={**self.headers, "Idempotency-Key": str(uuid4())},
            json={**self.receipt_payload, "owner_id": response.json()["id"]},
        )
        self.assertEqual(response.status_code, 404, response.text)

    async def test_tenant_actor_scope_and_auth_csrf(self) -> None:
        key = str(uuid4())
        first = await self.create_receipt(key=key)
        original = self.app.state.test_context
        self.app.state.test_context = replace(
            original, principal=replace(original.principal, user_id=str(uuid4()))
        )
        try:
            self.assertNotEqual((await self.create_receipt(key=key))["id"], first["id"])
        finally:
            self.app.state.test_context = original
        self.app.state.test_context = replace(
            original, principal=replace(original.principal, tenant_id=str(self.other))
        )
        try:
            self.assertEqual((await self.client.get(self.receipts)).json()["total"], 0)
            self.assertEqual(
                (await self.client.get(f"{self.receipts}/{first['id']}")).status_code,
                404,
            )
        finally:
            self.app.state.test_context = original
        self.assertEqual(
            (
                await self.client.post(self.receipts, json=self.receipt_payload)
            ).status_code,
            403,
        )
        self.assertEqual(
            (
                await self.client.post(
                    self.receipts, headers=self.headers, json=self.receipt_payload
                )
            ).status_code,
            422,
        )
        self.app.state.test_context = replace(original, principal=None)
        try:
            self.assertEqual((await self.client.get(self.receipts)).status_code, 401)
        finally:
            self.app.state.test_context = original

    async def test_create_holds_owner_reference_until_commit(self) -> None:
        """Удаление, начатое после проверки владельца, ожидает создание и получает конфликт."""
        entered, release = asyncio.Event(), asyncio.Event()
        original = CrmStockOwnerReference.get

        async def held(
            adapter: CrmStockOwnerReference, identifier: UUID, *, lock: bool = False
        ) -> StockOwnerReference | None:
            """Удерживает блокировку ссылки до запуска конкурентного удаления."""
            result = await original(adapter, identifier, lock=lock)
            if lock:
                entered.set()
                await release.wait()
            return result

        with patch.object(CrmStockOwnerReference, "get", held):
            create = asyncio.create_task(
                self.client.post(
                    self.receipts,
                    headers={**self.headers, "Idempotency-Key": str(uuid4())},
                    json=self.receipt_payload,
                )
            )
            await asyncio.wait_for(entered.wait(), 5)
            delete = asyncio.create_task(
                self.client.delete(
                    f"/api/console/crm/companies/{self.company['id']}",
                    headers=self.headers,
                )
            )
            try:
                await asyncio.sleep(0.05)
                self.assertFalse(delete.done())
            finally:
                release.set()
            created, deleted = await asyncio.gather(create, delete)
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(deleted.status_code, 409, deleted.text)

    async def test_deleted_owner_is_not_accepted_after_waiting(self) -> None:
        """Создание ждёт уже начатое удаление владельца и не сохраняет документ с чужой ссылкой."""
        entered, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyCompanyRepository.delete

        async def held(
            repository: SqlAlchemyCompanyRepository, company: CompanyEntity
        ) -> None:
            """Удерживает блокировку удаляемой компании до запуска создания документа."""
            entered.set()
            await release.wait()
            return await original(repository, company)

        with patch.object(SqlAlchemyCompanyRepository, "delete", held):
            delete = asyncio.create_task(
                self.client.delete(
                    f"/api/console/crm/companies/{self.company['id']}",
                    headers=self.headers,
                )
            )
            await asyncio.wait_for(entered.wait(), 5)
            create = asyncio.create_task(
                self.client.post(
                    self.receipts,
                    headers={**self.headers, "Idempotency-Key": str(uuid4())},
                    json=self.receipt_payload,
                )
            )
            try:
                await asyncio.sleep(0.05)
                self.assertFalse(create.done())
            finally:
                release.set()
            deleted, created = await asyncio.gather(delete, create)
        self.assertEqual(deleted.status_code, 204, deleted.text)
        self.assertEqual(created.status_code, 404, created.text)
        self.assertEqual((await self.client.get(self.receipts)).json()["total"], 0)

    async def test_migration_round_trip(self) -> None:
        async with self.engine.begin() as connection:
            migrator = TenantMigrator()
            schema = self.schemas[1]
            await migrator.downgrade(connection, schema, "0024_supplier_sources")
            self.assertEqual(
                await migrator.current(connection, schema), ("0024_supplier_sources",)
            )
            await migrator.upgrade(connection, schema)
            self.assertEqual(
                await migrator.current(connection, schema), (migrator.head(),)
            )
