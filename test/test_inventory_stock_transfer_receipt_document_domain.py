"""Планы приёмки StockTransfer: парные документы T → B, актуальный баланс и основания двух этапов."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_stock_transfer_receipt_domain as receipt_fixture
from src.modules.inventory.domain.error import InventoryError, QuantityStepError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.stock_transfer_dispatch_document import (
    StockTransferDispatchDocumentPolicy,
)
from src.modules.inventory.domain.policy.stock_transfer_document_source import (
    StockTransferDocumentSourcePolicy,
)
from src.modules.inventory.domain.policy.stock_transfer_receipt import (
    StockTransferReceiptPolicy,
)
from src.modules.inventory.domain.policy.stock_transfer_receipt_document import (
    StockTransferReceiptDocumentPolicy,
)
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.error import (
    EmptyStockDocumentError,
    InvalidStockDocumentContextError,
    StockDocumentNotDraftError,
    StockDocumentTimeError,
    StockDocumentUomMismatchError,
    InvalidStockTransferReceiptDocumentLineBindingError,
    InvalidStockDocumentTransferReceiptSnapshotError,
    StockDocumentTransferReceiptMismatchError,
    StockDocumentTransferReceiptQuantityExceededError,
    UnbalancedStockTransferReceiptDocumentsError,
    StaleStockTransferDocumentSourceError,
    StockDocumentTransferDispatchMismatchError,
)
from src.modules.inventory.domain.stock_document.transfer_receipt_snapshot import (
    StockDocumentTransferReceiptSnapshot,
)
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_source import (
    DocumentLineSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_document.value_object.transfer_receipt_line_binding import (
    StockTransferReceiptDocumentLineBindingVO,
)
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.issue_route import (
    IssueExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.receipt_route import (
    ReceiptExecutionRouteVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferTransitBalanceError,
    StockTransferVersionConflictError,
    StockTransferStatusError,
    StockTransferTransitStockExceededError,
)
from src.modules.inventory.domain.stock_transfer.value_object.identifier import (
    StockTransferIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.line_id import (
    StockTransferLineIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.status import (
    StockTransferStatus,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import WarehouseInactiveError
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class StockTransferReceiptDocumentDomainTests(unittest.TestCase):
    """Проверяет самостоятельные планы приёмки без резервирования транзита и автоматической регистрации фактов."""

    def setUp(self) -> None:
        """Готовит план 50 KG, принятую отправку 20 в T и два черновика приёмки на 20."""
        self.f = receipt_fixture.StockTransferReceiptDomainTests()
        self.f.setUp()
        self.d = self.f.d
        self.time = self.f.time
        self.bindings = self.new_bindings()
        self.issue_document, self.receipt_document = self.build(), self.build(
            StockOperationType.RECEIPT
        )

    def new_bindings(self) -> tuple[StockTransferReceiptDocumentLineBindingVO, ...]:
        """Передаёт новые ID обеих сторон ровно для положительных непринятых остатков."""
        return tuple(
            StockTransferReceiptDocumentLineBindingVO(
                line.id, StockDocumentLineIdVO(uuid4()), StockDocumentLineIdVO(uuid4())
            )
            for line in self.f.transfer.lines
            if line.dispatched_qty != line.received_qty
        )

    def build(
        self,
        operation_type: StockOperationType = StockOperationType.ISSUE,
        **changes: object,
    ) -> StockDocument:
        """Строит выбранный самостоятельный документ по свежему плану и балансу истории."""
        return StockDocument.create_from_stock_transfer_receipt(
            **(
                dict(
                    identifier=StockDocumentIdVO(uuid4()),
                    operation_type=operation_type,
                    transfer=self.f.transfer.receipt_snapshot(),
                    balance=self.f.balance(),
                    transit_warehouse=self.d.transit_warehouse,
                    destination_warehouse=self.d.f.destination,
                    inventory_items=(self.d.f.item.document_snapshot(),),
                    line_bindings=self.bindings,
                    created_at=self.time,
                )
                | changes
            )
        )

    def confirm(self, document: StockDocument, **changes: object) -> StockDocument:
        """Подтверждает по текущим T/B, остатку и снимку другой стороны до исполнения."""
        issue = document.operation_type is StockOperationType.ISSUE
        companion = self.receipt_document if issue else self.issue_document
        return document.confirm(
            **(
                dict(
                    warehouse=(
                        self.d.transit_warehouse if issue else self.d.f.destination
                    ),
                    inventory_items=(self.d.f.item.document_snapshot(),),
                    updated_at=self.time,
                    receipt_transfer=self.f.transfer.receipt_snapshot(),
                    receipt_balance=self.f.balance(),
                    receipt_companion_document=companion.transfer_receipt_snapshot(),
                    receipt_warehouses=(self.d.transit_warehouse, self.d.f.destination),
                )
                | changes
            )
        )

    def restore(self, document: StockDocument, **changes: object) -> StockDocument:
        """Восстанавливает только собственный исторический состав без актуального основания или баланса."""
        return StockDocument.restore(
            **(
                dict(
                    identifier=document.id,
                    operation_type=document.operation_type,
                    warehouse_id=document.warehouse_id,
                    owner_id=document.owner_id,
                    source=document.source,
                    status=document.status,
                    lines=document.lines,
                    created_at=document.created_at,
                    updated_at=document.updated_at,
                    version=document.version,
                )
                | changes
            )
        )

    def change(self, document: StockDocument, value: str) -> StockDocument:
        """Меняет количество через метод документа с сохранением SKU и основания строки."""
        return document.change_line(
            identifier=document.lines[0].id,
            quantity=QuantityVO(Decimal(value)),
            uom=self.d.f.item.base_uom,
            inventory_item=self.d.f.item.document_snapshot(),
            updated_at=self.time,
        )

    def fact(self, document: StockDocument, amounts: tuple[str, ...]) -> StockExecution:
        """Создаёт реальное исполнение приёмочного документа с его ID/версией и физическим маршрутом."""
        issue = document.operation_type is StockOperationType.ISSUE
        dimensions = (
            self.d.transit_dimensions if issue else self.f.destination_dimensions
        )
        route = (
            IssueExecutionRouteVO(dimensions)
            if issue
            else ReceiptExecutionRouteVO(dimensions)
        )
        return StockExecution.create(
            identifier=StockExecutionIdVO(uuid4()),
            document=document.execution_snapshot(),
            executed_at=self.time,
            warehouse=self.d.transit_warehouse if issue else self.d.f.destination,
            inventory_items=(self.d.f.item.execution_snapshot(),),
            locations=(
                self.d.transit_location if issue else self.f.destination_location,
            ),
            lines=tuple(
                StockExecutionLine.create(
                    identifier=StockExecutionLineIdVO(uuid4()),
                    document_line_id=document.lines[0].id,
                    inventory_item=self.d.f.item.execution_snapshot(),
                    quantity=QuantityVO(Decimal(value)),
                    uom=self.d.f.item.base_uom,
                    route=route,
                )
                for value in amounts
            ),
        )

    def accept(self, issue: StockExecution, receipt: StockExecution) -> None:
        """Использует прежнюю приёмку с явными назначениями и фиксирует историю в тестовой модели."""
        result = StockTransferReceiptPolicy.build_receipt(
            transfer=self.f.transfer.receipt_snapshot(),
            balance=self.f.balance(),
            issue=issue.transfer_snapshot(),
            receipt=receipt.transfer_snapshot(),
            transit_warehouse=self.d.transit_warehouse,
            destination_warehouse=self.d.f.destination,
            locations=(self.d.transit_location, self.f.destination_location),
            issue_bindings=self.f.bindings(issue),
            receipt_bindings=self.f.bindings(receipt),
        )
        transfer = self.f.transfer.register_receipt(
            result, expected_version=self.f.transfer.version, updated_at=self.time
        )
        self.issue_document = self.issue_document.register_execution(
            issue.snapshot_for_document(), updated_at=self.time
        )
        self.receipt_document = self.receipt_document.register_execution(
            receipt.snapshot_for_document(), updated_at=self.time
        )
        self.f.transfer = transfer
        self.f.receipts += (result,)
        self.f.executions += (issue.transfer_snapshot(),)

    def test_factory_plans_only_in_transit_quantity_and_does_not_change_roots(
        self,
    ) -> None:
        """Из плана 50 при отправке 20 получаются два отдельных DRAFT v0 на 20, а не на 50."""
        for document, warehouse in (
            (self.issue_document, self.d.transit_warehouse),
            (self.receipt_document, self.d.f.destination),
        ):
            self.assertEqual(
                (document.status, document.version, document.warehouse_id),
                (StockDocumentStatus.DRAFT, 0, warehouse.id),
            )
            line = document.lines[0]
            self.assertEqual(
                (
                    line.planned_qty.value,
                    line.executed_qty.value,
                    line.conversion.factor_to_base,
                ),
                (Decimal(20), Decimal(0), Decimal(1)),
            )
            self.assertEqual(line.sku, self.d.f.item.sku)
            self.assertEqual(line.base_uom, UomCodeVO("KG"))
        self.assertNotEqual(self.issue_document.id, self.receipt_document.id)
        self.assertEqual(
            self.issue_document.lines[0].id, self.bindings[0].issue_document_line_id
        )
        self.assertEqual(
            self.receipt_document.lines[0].id, self.bindings[0].receipt_document_line_id
        )
        self.assertEqual(
            (
                self.f.transfer.version,
                self.f.transfer.lines[0].dispatched_qty.value,
                self.f.transfer.lines[0].received_qty.value,
            ),
            (3, Decimal(20), Decimal(0)),
        )
        self.assertEqual(self.f.transfer.transit, self.d.transit)

    def test_factory_uses_remaining_after_partial_receipt(self) -> None:
        """После приёмки 10 из отправленных 20 новые планы равны 10; неотправленные 30 не учитываются."""
        self.f.accept()
        self.assertEqual(self.build().lines[0].planned_qty.value, Decimal(10))
        self.assertEqual(self.build(StockOperationType.RECEIPT).source.version, 4)

    def test_empty_transit_cannot_plan_receipt_even_when_transfer_has_undispatched_quantity(
        self,
    ) -> None:
        """Нулевой непринятый остаток блокирует фабрику при ещё открытом плане 50."""
        self.f.issue, self.f.receipt = self.f.fact(
            StockOperationType.ISSUE, ("20",)
        ), self.f.fact(StockOperationType.RECEIPT, ("20",))
        self.f.accept()
        self.assertEqual(self.f.transfer.status, StockTransferStatus.IN_PROGRESS)
        with self.assertRaises(EmptyStockDocumentError):
            self.build(line_bindings=())

    def test_factory_requires_in_progress_transfer(self) -> None:
        """Подтверждённый план до отправки, черновик и завершённое перемещение не допускаются."""
        for transfer in (
            self.d.transfer,
            self.d.f.add(),
            self.d.f.cancel(self.d.f.add()),
        ):
            with self.assertRaises(StockTransferStatusError):
                self.build(transfer=transfer.receipt_snapshot())
        complete = replace(
            self.f.transfer.lines[0],
            dispatched_qty=self.f.transfer.lines[0].planned_qty,
            received_qty=self.f.transfer.lines[0].planned_qty,
        )
        restored = self.d.restore(
            self.f.transfer, status=StockTransferStatus.COMPLETED, lines=(complete,)
        )
        with self.assertRaises(StockTransferStatusError):
            self.build(transfer=restored.receipt_snapshot())

    def test_source_records_receipt_phase_and_preserves_canonical_line_refs(
        self,
    ) -> None:
        """Этап приёмки имеет отдельные системы шапки и общий канонический TransferLine."""
        for document, system in (
            (
                self.issue_document,
                StockTransferReceiptDocumentPolicy.ISSUE_SOURCE_SYSTEM,
            ),
            (
                self.receipt_document,
                StockTransferReceiptDocumentPolicy.RECEIPT_SOURCE_SYSTEM,
            ),
        ):
            self.assertEqual(
                document.source,
                DocumentSourceVO(system, str(self.f.transfer.id.uuid), 3),
            )
            self.assertEqual(
                document.lines[0].source,
                DocumentLineSourceVO(
                    StockTransferDocumentSourcePolicy.LINE_SOURCE_SYSTEM,
                    str(self.d.f.line.id.uuid),
                ),
            )
            self.assertEqual(
                document.transfer_receipt_snapshot().source_transfer_version, 3
            )
            with self.assertRaises(StockDocumentTransferDispatchMismatchError):
                document.transfer_dispatch_snapshot()

    def test_binding_types_duplicates_and_coverage_are_enforced(self) -> None:
        """Новые ID обеих сторон уникальны и назначают ровно положительные остатки, а не любой план."""
        binding = self.bindings[0]
        for changes in (
            dict(transfer_line_id=uuid4()),
            dict(issue_document_line_id=None),
            dict(receipt_document_line_id=binding.issue_document_line_id),
        ):
            with self.assertRaises(InvalidStockTransferReceiptDocumentLineBindingError):
                replace(binding, **changes)
        for values in (
            (),
            self.bindings * 2,
            list(self.bindings),
            (None,),
            (replace(binding, transfer_line_id=StockTransferLineIdVO(uuid4())),),
        ):
            with self.assertRaises(InvalidStockTransferReceiptDocumentLineBindingError):
                self.build(line_bindings=values)
        with self.assertRaises(FrozenInstanceError):
            binding.transfer_line_id = StockTransferLineIdVO(uuid4())

    def test_factory_requires_exact_item_snapshots_current_uom_step_and_sku(
        self,
    ) -> None:
        """Количество приёмки проверяется текущими правилами, SKU фиксируется из текущего товара."""
        item = self.d.f.item.document_snapshot()
        for values in (
            (),
            (item, item),
            [item],
            (None,),
            (replace(item, inventory_item_id=InventoryItemIdVO(uuid4())),),
        ):
            with self.assertRaises(InventoryError):
                self.build(inventory_items=values)
        with self.assertRaises(StockDocumentUomMismatchError):
            self.build(inventory_items=(replace(item, base_uom=UomCodeVO("G")),))
        with self.assertRaises(QuantityStepError):
            self.build(
                inventory_items=(
                    replace(item, quantity_rules=QuantityRulesVO(Decimal(3))),
                )
            )
        self.assertEqual(
            self.build(inventory_items=(replace(item, sku=SkuVO("CURRENT")),))
            .lines[0]
            .sku,
            SkuVO("CURRENT"),
        )

    def test_source_warehouse_can_be_inactive_after_dispatch(self) -> None:
        """Для T → B активность A не нужна ни при создании, ни при подтверждении."""
        self.d.f.source = replace(self.d.f.source, is_active=False)
        self.assertEqual(self.build().lines[0].planned_qty.value, Decimal(20))
        self.assertEqual(
            self.confirm(self.issue_document).status, StockDocumentStatus.CONFIRMED
        )

    def test_factory_and_confirmation_require_active_t_b_in_correct_roles(self) -> None:
        """Неактивные или чужие T/B и передача A вместо нужной стороны запрещены."""
        for name, warehouse in (
            ("transit_warehouse", self.d.transit_warehouse),
            ("destination_warehouse", self.d.f.destination),
        ):
            with self.assertRaises(WarehouseInactiveError):
                self.build(**{name: replace(warehouse, is_active=False)})
        with self.assertRaises(InvalidStockDocumentContextError):
            self.build(
                transit_warehouse=self.d.f.destination,
                destination_warehouse=self.d.transit_warehouse,
            )
        for warehouses in (
            (replace(self.d.transit_warehouse, is_active=False), self.d.f.destination),
            (self.d.transit_warehouse, replace(self.d.f.destination, is_active=False)),
        ):
            with self.assertRaises(WarehouseInactiveError):
                self.confirm(self.issue_document, receipt_warehouses=warehouses)
        for warehouses in (
            (self.d.transit_warehouse,),
            (self.d.transit_warehouse, self.d.f.destination, self.d.f.source),
            (self.d.transit_warehouse, self.d.f.destination, self.d.f.destination),
            [self.d.transit_warehouse, self.d.f.destination],
        ):
            with self.assertRaises(InventoryError):
                self.confirm(self.issue_document, receipt_warehouses=warehouses)

    def test_factory_rejects_unsupported_operation(self) -> None:
        """Роль приёмки выбирается только для ISSUE T или RECEIPT B."""
        for operation in (StockOperationType.INTERNAL_MOVE, "ISSUE", None):
            with self.assertRaises(StockDocumentTransferReceiptMismatchError):
                self.build(operation_type=operation)

    def test_stale_balance_is_rejected_at_creation_and_confirmation(self) -> None:
        """После прогресса перемещения старый состав транзита не считается актуальным."""
        old = self.f.balance()
        self.f.accept()
        for action in (
            lambda: self.build(balance=old),
            lambda: self.confirm(self.issue_document, receipt_balance=old),
        ):
            with self.assertRaises(StockTransferVersionConflictError):
                action()

    def test_balance_must_match_transfer_scope_and_current_total(self) -> None:
        """Чужой или несогласованный остаток не подтверждает непринятую отправку этого перемещения."""
        balance = self.f.balance()
        for changes in (
            dict(transfer_id=StockTransferIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(lines=()),
            dict(lines=(replace(balance.lines[0], quantity=QuantityVO(Decimal(19))),)),
        ):
            with self.assertRaises(InvalidStockTransferTransitBalanceError):
                self.build(balance=replace(balance, **changes))
            with self.assertRaises(InvalidStockTransferTransitBalanceError):
                self.confirm(
                    self.issue_document, receipt_balance=replace(balance, **changes)
                )

    def test_confirm_both_sides_keeps_transfer_and_originals_unchanged(self) -> None:
        """Два CONFIRMED v1 не меняют принятый транзит, счётчики или версии исходных корней."""
        issue = self.confirm(self.issue_document)
        receipt = self.confirm(
            self.receipt_document,
            receipt_companion_document=issue.transfer_receipt_snapshot(),
        )
        self.assertEqual(
            (issue.version, receipt.version, issue.status, receipt.status),
            (1, 1, StockDocumentStatus.CONFIRMED, StockDocumentStatus.CONFIRMED),
        )
        self.assertEqual(self.issue_document.status, StockDocumentStatus.DRAFT)
        self.assertEqual(self.f.transfer.version, 3)
        self.assertEqual(self.f.transfer.lines[0].received_qty.value, Decimal(0))
        with self.assertRaises(FrozenInstanceError):
            issue.version = 5

    def test_confirmation_requires_receipt_plan_balance_companion_and_warehouses(
        self,
    ) -> None:
        """Пропуск любого контракта и передача полных корней вместо снимков не обходят проверку confirm()."""
        for changes in (
            dict(receipt_transfer=None),
            dict(receipt_transfer=self.f.transfer),
            dict(receipt_balance=None),
            dict(receipt_companion_document=None),
            dict(receipt_companion_document=self.receipt_document),
            dict(receipt_warehouses=None),
        ):
            with self.assertRaises(InventoryError):
                self.confirm(self.issue_document, **changes)
        with self.assertRaises(InventoryError):
            self.issue_document.confirm(
                warehouse=self.d.transit_warehouse,
                inventory_items=(self.d.f.item.document_snapshot(),),
                updated_at=self.time,
            )

    def test_fresh_balance_does_not_silently_rebase_stale_document_source(self) -> None:
        """Даже если остаток ещё положителен, новый баланс не меняет сохранённую source.version старого черновика."""
        self.f.accept()
        with self.assertRaises(StaleStockTransferDocumentSourceError):
            self.confirm(self.issue_document)
        self.assertEqual(self.issue_document.source.version, 3)

    def test_pair_plans_must_match_after_edits_and_cannot_exceed_transit(self) -> None:
        """Одностороннее изменение блокирует подтверждение; равные 21/21 превышают остаток 20."""
        small = self.change(self.issue_document, "10")
        with self.assertRaises(UnbalancedStockTransferReceiptDocumentsError):
            self.confirm(small)
        peer = self.change(self.receipt_document, "10")
        self.assertEqual(
            self.confirm(
                small, receipt_companion_document=peer.transfer_receipt_snapshot()
            )
            .lines[0]
            .planned_qty.value,
            Decimal(10),
        )
        self.assertEqual(small.lines[0].source, self.issue_document.lines[0].source)
        with self.assertRaises(StockDocumentTransferReceiptQuantityExceededError):
            self.confirm(
                self.change(self.issue_document, "21"),
                receipt_companion_document=self.change(
                    self.receipt_document, "21"
                ).transfer_receipt_snapshot(),
            )

    def test_pair_requires_matching_transfer_owner_roles_and_unique_ids(self) -> None:
        """Правильная сумма не исправляет чужие реквизиты или неправильную роль партнёра."""
        companion = self.receipt_document.transfer_receipt_snapshot()
        for changes in (
            dict(transfer_id=StockTransferIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(operation_type=StockOperationType.ISSUE),
            dict(id=self.issue_document.id),
            dict(warehouse_id=self.d.transit_warehouse.id),
        ):
            with self.assertRaises(StockDocumentTransferReceiptMismatchError):
                self.confirm(
                    self.issue_document,
                    receipt_companion_document=replace(companion, **changes),
                )
        with self.assertRaises(StockDocumentTransferReceiptMismatchError):
            self.confirm(
                self.issue_document,
                receipt_companion_document=replace(
                    companion,
                    lines=(
                        replace(
                            companion.lines[0],
                            document_line_id=self.issue_document.lines[0].id,
                        ),
                    ),
                ),
            )

    def test_pair_cannot_change_line_item_or_unit_on_both_sides(self) -> None:
        """Совпадение сторон проверяется и относительно текущего плана, а не только между собой."""
        a, b = (
            self.issue_document.transfer_receipt_snapshot(),
            self.receipt_document.transfer_receipt_snapshot(),
        )
        for changes in (
            dict(transfer_line_id=StockTransferLineIdVO(uuid4())),
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
        ):
            with self.assertRaises(StockDocumentTransferReceiptMismatchError):
                StockTransferReceiptDocumentPolicy.ensure_pair_compatible(
                    first=replace(a, lines=(replace(a.lines[0], **changes),)),
                    second=replace(b, lines=(replace(b.lines[0], **changes),)),
                    transfer=self.f.transfer.receipt_snapshot(),
                    balance=self.f.balance(),
                    warehouses=(self.d.transit_warehouse, self.d.f.destination),
                    as_of=self.time,
                )

    def test_cancelled_or_executing_companion_cannot_confirm_new_side(self) -> None:
        """Пару подтверждают до исполнения; отменённый или уже исполняемый партнёр не подходит."""
        cancelled = self.receipt_document.cancel(updated_at=self.time)
        with self.assertRaises(StockDocumentNotDraftError):
            self.confirm(
                self.issue_document,
                receipt_companion_document=cancelled.transfer_receipt_snapshot(),
            )
        active = self.confirm(self.receipt_document)
        fact = self.fact(active, ("10",))
        partial = active.register_execution(
            fact.snapshot_for_document(), updated_at=self.time
        )
        with self.assertRaises(StockDocumentNotDraftError):
            self.confirm(
                self.issue_document,
                receipt_companion_document=partial.transfer_receipt_snapshot(),
            )

    def test_restore_preserves_historical_source_without_current_context(self) -> None:
        """Восстановление не обращается к текущему перемещению, складам или балансу."""
        document = self.confirm(self.issue_document)
        self.f.accept()
        self.assertEqual(self.restore(document), document)
        self.assertEqual(self.restore(document).source.version, 3)

    def test_restore_rejects_wrong_role_missing_version_noncanonical_or_missing_refs(
        self,
    ) -> None:
        """Зарезервированные основания проверяются независимо от специальной фабрики."""
        for source in (
            replace(self.issue_document.source, version=None),
            replace(
                self.issue_document.source,
                system=StockTransferReceiptDocumentPolicy.RECEIPT_SOURCE_SYSTEM,
            ),
            replace(self.issue_document.source, reference="bad"),
            replace(
                self.issue_document.source,
                reference="{" + self.issue_document.source.reference + "}",
            ),
        ):
            with self.assertRaises(StockDocumentTransferReceiptMismatchError):
                self.restore(self.issue_document, source=source)
        for source in (
            None,
            DocumentLineSourceVO("other", "reference"),
            DocumentLineSourceVO(
                StockTransferReceiptDocumentPolicy.LINE_SOURCE_SYSTEM, "bad"
            ),
        ):
            with self.assertRaises(StockDocumentTransferReceiptMismatchError):
                self.restore(
                    self.issue_document,
                    lines=(replace(self.issue_document.lines[0], source=source),),
                )
        duplicate = replace(
            self.issue_document.lines[0], id=StockDocumentLineIdVO(uuid4())
        )
        with self.assertRaises(StockDocumentTransferReceiptMismatchError):
            self.restore(
                self.issue_document, lines=(self.issue_document.lines[0], duplicate)
            )
        with self.assertRaises(InventoryError):
            self.restore(self.issue_document, source=None)

    def test_source_policy_recognizes_both_phases_without_accepting_mixed_rows(
        self,
    ) -> None:
        """Один общий синтаксис сохраняет прежние источники отправки и разрешает отдельные источники приёмки."""
        StockTransferDispatchDocumentPolicy.ensure_document_source(
            operation_type=self.issue_document.operation_type,
            source=self.issue_document.source,
            lines=self.issue_document.lines,
        )
        dispatch_source = DocumentSourceVO(
            StockTransferDispatchDocumentPolicy.ISSUE_SOURCE_SYSTEM,
            str(self.f.transfer.id.uuid),
            3,
        )
        dispatch = self.restore(self.issue_document, source=dispatch_source)
        dispatch.transfer_dispatch_snapshot().ensure_valid()
        with self.assertRaises(StockDocumentTransferReceiptMismatchError):
            dispatch.transfer_receipt_snapshot()
        for source in (
            DocumentLineSourceVO("inventory.shipment_line", str(uuid4())),
            DocumentLineSourceVO(
                StockTransferReceiptDocumentPolicy.ISSUE_SOURCE_SYSTEM, str(uuid4())
            ),
        ):
            with self.assertRaises(InventoryError):
                self.restore(
                    self.issue_document,
                    lines=(replace(self.issue_document.lines[0], source=source),),
                )

    def test_dispatch_context_cannot_replace_receipt_context(self) -> None:
        """Контексты этапов не взаимозаменяемы даже при совпадении всех идентификаторов строк."""
        with self.assertRaises(InvalidStockDocumentContextError):
            self.confirm(
                self.issue_document,
                transfer=self.f.transfer.dispatch_document_snapshot(),
            )
        with self.assertRaises(InvalidStockDocumentTransferReceiptSnapshotError):
            source = DocumentSourceVO(
                StockTransferDispatchDocumentPolicy.RECEIPT_SOURCE_SYSTEM,
                str(self.f.transfer.id.uuid),
                3,
            )
            dispatch_peer = self.restore(self.receipt_document, source=source)
            self.confirm(
                self.issue_document,
                receipt_companion_document=dispatch_peer.transfer_dispatch_snapshot(),
            )

    def test_ordinary_document_rejects_receipt_context_and_keeps_old_confirm_contract(
        self,
    ) -> None:
        """Обычный документ не требует новых снимков, но не принимает лишний контекст приёмки."""
        ordinary = self.restore(
            self.issue_document,
            source=DocumentSourceVO("external", "ORDER-001"),
            lines=(replace(self.issue_document.lines[0], source=None),),
        )
        with self.assertRaises(InvalidStockDocumentContextError):
            self.confirm(ordinary)
        self.assertEqual(
            ordinary.confirm(
                warehouse=self.d.transit_warehouse,
                inventory_items=(self.d.f.item.document_snapshot(),),
                updated_at=self.time,
            ).status,
            StockDocumentStatus.CONFIRMED,
        )

    def test_snapshot_runtime_types_versions_and_progress_are_checked(self) -> None:
        """Сырые UUID, bool-версии, неправильные типы и повторы отвергаются потребителем снимков."""
        snapshot = self.receipt_document.transfer_receipt_snapshot()
        for changes in (
            dict(version=True),
            dict(source_transfer_version=True),
            dict(operation_type="RECEIPT"),
            dict(lines=list(snapshot.lines)),
            dict(lines=(snapshot.lines[0], snapshot.lines[0])),
            dict(updated_at=self.time.replace(tzinfo=None)),
            dict(
                lines=(replace(snapshot.lines[0], planned_qty=QuantityVO(Decimal(0))),)
            ),
        ):
            with self.assertRaises(InventoryError):
                self.confirm(
                    self.issue_document,
                    receipt_companion_document=replace(snapshot, **changes),
                )
        with self.assertRaises(FrozenInstanceError):
            snapshot.version = 1

    def test_explicit_monotonic_time_and_timezone_normalization(self) -> None:
        """Ранний или наивный момент запрещён, aware-ввод нормализуется в UTC."""
        for value in (
            self.time - timedelta(seconds=1),
            self.time.replace(tzinfo=None),
            None,
        ):
            with self.assertRaises(StockDocumentTimeError):
                self.build(created_at=value)
            with self.assertRaises(StockDocumentTimeError):
                self.confirm(self.issue_document, updated_at=value)
        future = replace(
            self.receipt_document.transfer_receipt_snapshot(),
            updated_at=self.time + timedelta(seconds=1),
        )
        with self.assertRaises(StockDocumentTimeError):
            self.confirm(self.issue_document, receipt_companion_document=future)
        local = self.time.astimezone(timezone(timedelta(hours=3)))
        self.assertEqual(
            self.build(created_at=local).created_at.utcoffset(), timedelta(0)
        )
        self.assertEqual(
            self.confirm(self.issue_document, updated_at=local).updated_at.utcoffset(),
            timedelta(0),
        )

    def test_current_quantity_rules_are_rechecked_on_confirm(self) -> None:
        """Подтверждение старого плана повторяет проверку текущего шага товара."""
        current = replace(
            self.d.f.item.document_snapshot(),
            quantity_rules=QuantityRulesVO(Decimal(3)),
        )
        with self.assertRaises(QuantityStepError):
            self.confirm(self.issue_document, inventory_items=(current,))

    def test_lot_balance_is_aggregated_for_plan_but_specific_lot_is_checked_on_execution(
        self,
    ) -> None:
        """План 20 не выбирает LOT: при A=8/B=12 фактическая приёмка 10 A остаётся запрещённой."""
        balance = self.f.balance()
        a, b = StockLotIdVO(uuid4()), StockLotIdVO(uuid4())
        row = balance.lines[0]
        balance = replace(
            balance,
            lines=(
                replace(
                    row,
                    quantity=QuantityVO(Decimal(8)),
                    dimensions=replace(row.dimensions, lot_id=a),
                ),
                replace(
                    row,
                    quantity=QuantityVO(Decimal(12)),
                    dimensions=replace(row.dimensions, lot_id=b),
                ),
            ),
        )
        lot_item = replace(
            self.d.f.item.document_snapshot(), tracking_mode=TrackingMode.LOT
        )
        document = self.build(balance=balance, inventory_items=(lot_item,))
        self.assertEqual(
            self.confirm(document, receipt_balance=balance, inventory_items=(lot_item,))
            .lines[0]
            .planned_qty.value,
            Decimal(20),
        )
        issue = self.f.issue.transfer_snapshot()
        receipt = self.f.receipt.transfer_snapshot()
        issue = replace(
            issue,
            lines=tuple(
                replace(line, dimensions=replace(line.dimensions, lot_id=a))
                for line in issue.lines
            ),
        )
        receipt = replace(
            receipt,
            lines=tuple(
                replace(line, dimensions=replace(line.dimensions, lot_id=a))
                for line in receipt.lines
            ),
        )
        with self.assertRaises(StockTransferTransitStockExceededError):
            self.f.build(balance=balance, issue=issue, receipt=receipt)

    def test_serial_receipt_plan_counts_pcs_without_selecting_series_in_document_lines(
        self,
    ) -> None:
        """Состав трёх серий по 1 PCS даёт одну плановую строку 3 PCS без хранения сериалов в документе."""
        transfer = self.f.transfer.receipt_snapshot()
        transfer = replace(
            transfer,
            lines=(
                replace(
                    transfer.lines[0],
                    base_uom=UomCodeVO("PCS"),
                    dispatched_qty=QuantityVO(Decimal(3)),
                ),
            ),
        )
        balance = self.f.balance()
        row = balance.lines[0]
        balance = replace(
            balance,
            lines=tuple(
                replace(
                    row,
                    base_uom=UomCodeVO("PCS"),
                    quantity=QuantityVO(Decimal(1)),
                    dimensions=replace(
                        row.dimensions, serial_id=StockSerialIdVO(uuid4())
                    ),
                )
                for _ in range(3)
            ),
        )
        item = replace(
            self.d.f.item.document_snapshot(),
            base_uom=UomCodeVO("PCS"),
            tracking_mode=TrackingMode.SERIAL,
            quantity_rules=QuantityRulesVO(Decimal(1)),
        )
        document = self.build(
            transfer=transfer, balance=balance, inventory_items=(item,)
        )
        self.assertEqual(
            (document.lines[0].planned_qty.value, document.lines[0].base_uom),
            (Decimal(3), UomCodeVO("PCS")),
        )

    def test_multiple_lines_of_same_item_keep_separate_balances_and_bindings(
        self,
    ) -> None:
        """Один товар в двух строках не объединяется; неотправленные строки не попадают в документы."""
        plan = self.f.transfer.receipt_snapshot()
        first = replace(plan.lines[0], dispatched_qty=QuantityVO(Decimal(8)))
        second = replace(
            plan.lines[0],
            id=StockTransferLineIdVO(uuid4()),
            dispatched_qty=QuantityVO(Decimal(12)),
        )
        undispatched = replace(
            plan.lines[0],
            id=StockTransferLineIdVO(uuid4()),
            dispatched_qty=QuantityVO(Decimal(0)),
        )
        already_received = replace(
            plan.lines[0],
            id=StockTransferLineIdVO(uuid4()),
            dispatched_qty=QuantityVO(Decimal(7)),
            received_qty=QuantityVO(Decimal(7)),
        )
        plan = replace(plan, lines=(first, second, undispatched, already_received))
        balance = self.f.balance()
        balance = replace(
            balance,
            lines=(
                replace(
                    balance.lines[0],
                    transfer_line_id=first.id,
                    quantity=QuantityVO(Decimal(8)),
                ),
                replace(
                    balance.lines[0],
                    transfer_line_id=second.id,
                    quantity=QuantityVO(Decimal(12)),
                ),
            ),
        )
        bindings = tuple(
            StockTransferReceiptDocumentLineBindingVO(
                row.id, StockDocumentLineIdVO(uuid4()), StockDocumentLineIdVO(uuid4())
            )
            for row in (first, second)
        )
        a = self.build(transfer=plan, balance=balance, line_bindings=bindings)
        b = self.build(
            StockOperationType.RECEIPT,
            transfer=plan,
            balance=balance,
            line_bindings=bindings,
        )
        self.assertEqual(
            {line.planned_qty.value for line in a.lines}, {Decimal(8), Decimal(12)}
        )
        self.assertEqual(len(a.lines), 2)
        self.assertEqual(
            self.confirm(
                a,
                receipt_transfer=plan,
                receipt_balance=balance,
                receipt_companion_document=b.transfer_receipt_snapshot(),
            ).status,
            StockDocumentStatus.CONFIRMED,
        )
        a_snapshot, b_snapshot = (
            a.transfer_receipt_snapshot(),
            b.transfer_receipt_snapshot(),
        )

        def swapped(
            snapshot: StockDocumentTransferReceiptSnapshot,
        ) -> StockDocumentTransferReceiptSnapshot:
            """Меняет количества между обязательствами одного товара, сохраняя общую сумму 20."""
            return replace(
                snapshot,
                lines=tuple(
                    replace(
                        line,
                        planned_qty=QuantityVO(
                            Decimal(12 if line.transfer_line_id == first.id else 8)
                        ),
                    )
                    for line in snapshot.lines
                ),
            )

        with self.assertRaises(StockDocumentTransferReceiptQuantityExceededError):
            StockTransferReceiptDocumentPolicy.ensure_pair_compatible(
                first=swapped(a_snapshot),
                second=swapped(b_snapshot),
                transfer=plan,
                balance=balance,
                warehouses=(self.d.transit_warehouse, self.d.f.destination),
                as_of=self.time,
            )
        repeated = (
            bindings[0],
            replace(
                bindings[1], issue_document_line_id=bindings[0].receipt_document_line_id
            ),
        )
        with self.assertRaises(InvalidStockTransferReceiptDocumentLineBindingError):
            self.build(transfer=plan, balance=balance, line_bindings=repeated)

    def test_historical_document_basis_allows_partial_execution_without_reconfirmation(
        self,
    ) -> None:
        """Два исполнения 10+10 завершают документы на 20, сохраняя source.version=3 и открытый план перемещения."""
        self.issue_document = self.confirm(self.issue_document)
        self.receipt_document = self.confirm(self.receipt_document)
        for _ in range(2):
            self.accept(
                self.fact(self.issue_document, ("10",)),
                self.fact(self.receipt_document, ("4", "6")),
            )
            self.assertEqual(self.issue_document.source.version, 3)
        self.assertEqual(
            (self.issue_document.status, self.receipt_document.status),
            (StockDocumentStatus.COMPLETED, StockDocumentStatus.COMPLETED),
        )
        self.assertEqual(
            (self.f.transfer.status, self.f.transfer.lines[0].received_qty.value),
            (StockTransferStatus.IN_PROGRESS, Decimal(20)),
        )
        self.assertEqual(
            self.f.transfer.lines[0].remaining_to_dispatch_qty().value, Decimal(30)
        )
        self.assertEqual(self.f.balance().lines, ())

    def test_receiving_all_planned_goods_completes_transfer_with_old_physical_mechanism(
        self,
    ) -> None:
        """После отправки всех 50 приёмка 20+30 завершает документы и StockTransfer без нового механизма учёта."""
        out = self.d.fact(StockOperationType.ISSUE, ("30",))
        inc = self.d.fact(StockOperationType.RECEIPT, ("30",))
        dispatch = self.d.build(
            transfer=self.f.transfer.dispatch_snapshot(),
            issue=out.transfer_snapshot(),
            receipt=inc.transfer_snapshot(),
            issue_bindings=self.d.bindings(out),
            receipt_bindings=self.d.bindings(inc),
        )
        self.f.transfer = self.d.register(dispatch, self.f.transfer)
        self.f.dispatches += (dispatch,)
        self.f.executions += (inc.transfer_snapshot(),)
        self.bindings = self.new_bindings()
        self.issue_document, self.receipt_document = self.build(), self.build(
            StockOperationType.RECEIPT
        )
        self.issue_document, self.receipt_document = self.confirm(
            self.issue_document
        ), self.confirm(self.receipt_document)
        # Исторические позиции соответствуют уже принятой отправке всего плана.
        transit = replace(self.d.transit_position, on_hand_qty=QuantityVO(Decimal(50)))
        destination = replace(
            self.d.transit_position,
            id=StockPositionIdVO(uuid4()),
            dimensions=self.f.destination_dimensions,
        )
        for value in ("20", "30"):
            issue, receipt = self.fact(self.issue_document, (value,)), self.fact(
                self.receipt_document, (value,)
            )
            outgoing = self.d.posting(issue, transit, self.d.transit_location)
            incoming = self.d.posting(receipt, destination, self.f.destination_location)
            self.assertEqual(outgoing.posted_at, incoming.posted_at)
            transit = transit.apply_posting_entry(
                outgoing.entries[0].snapshot(),
                expected_version=transit.version,
                inventory_item=self.d.f.item.stock_snapshot(),
                location=self.d.transit_location,
                warehouse=self.d.transit_warehouse,
            )
            destination = destination.apply_posting_entry(
                incoming.entries[0].snapshot(),
                expected_version=destination.version,
                inventory_item=self.d.f.item.stock_snapshot(),
                location=self.f.destination_location,
                warehouse=self.d.f.destination,
            )
            self.accept(issue, receipt)
            self.assertEqual(
                transit.on_hand_qty.value + destination.on_hand_qty.value, Decimal(50)
            )
        self.assertEqual(self.f.transfer.status, StockTransferStatus.COMPLETED)
        self.assertEqual(
            (transit.on_hand_qty.value, destination.on_hand_qty.value),
            (Decimal(0), Decimal(50)),
        )
        self.assertEqual(self.issue_document.source.version, 4)
        self.assertEqual(self.f.transfer.version, 6)

    def test_hostile_decimal_context_preserves_transit_subtraction_and_document_quantity(
        self,
    ) -> None:
        """Остаток 20−10 и базовый план не зависят от внешней точности Decimal."""
        self.f.accept()
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            self.issue_document, self.receipt_document = self.build(), self.build(
                StockOperationType.RECEIPT
            )
            self.assertEqual(
                self.confirm(self.issue_document).lines[0].planned_qty.value,
                Decimal(10),
            )

    def test_planning_another_pair_does_not_reserve_or_consume_transit(self) -> None:
        """Несколько планов сами по себе не меняют остаток или версию перемещения; глобальное распределение относится к хранению."""
        self.bindings = self.new_bindings()
        another_a, another_b = self.build(), self.build(StockOperationType.RECEIPT)
        self.assertEqual(
            self.confirm(
                another_a,
                receipt_companion_document=another_b.transfer_receipt_snapshot(),
            ).status,
            StockDocumentStatus.CONFIRMED,
        )
        self.assertEqual(self.f.transfer.lines[0].received_qty.value, Decimal(0))
        self.assertEqual(self.f.balance().lines[0].quantity.value, Decimal(20))


if __name__ == "__main__":
    unittest.main()
