"""Автоматическая регистрация приёмки по документам T → B: связи, версии, лимиты и текущий LOT/SERIAL-баланс."""

import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import (
    test_inventory_stock_transfer_receipt_document_domain as document_fixture,
)
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.stock_transfer_receipt import (
    StockTransferReceiptPolicy,
)
from src.modules.inventory.domain.policy.stock_transfer_document_execution import (
    StockTransferDocumentExecutionPolicy,
)
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.transfer_dispatch_snapshot import (
    StockDocumentTransferDispatchSnapshot,
)
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentContextError,
    InvalidStockDocumentTransferReceiptSnapshotError,
    StockDocumentExecutionNotAllowedError,
    StockDocumentOverExecutionError,
    StaleStockDocumentVersionError,
)
from src.modules.inventory.domain.stock_document.transfer_receipt_snapshot import (
    StockDocumentTransferReceiptSnapshot,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_execution.transfer_document_snapshot import (
    StockExecutionTransferDocumentSnapshot,
)
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.error import StockExecutionTimeError
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
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
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
    StockTransferReceiptMismatchError,
    StockTransferTransitStockExceededError,
    StockTransferVersionConflictError,
    StockTransferTimeError,
    StockTransferStatusError,
    UnbalancedStockTransferReceiptError,
)
from src.modules.inventory.domain.stock_transfer.receipt_snapshot import (
    StockTransferReceiptSnapshot,
)
from src.modules.inventory.domain.stock_transfer.value_object.execution_binding import (
    StockTransferExecutionBindingVO,
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
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import WarehouseInactiveError
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class StockTransferReceiptDocumentExecutionDomainTests(unittest.TestCase):
    """Проверяет общий документный путь и отдельные правила актуального транзита без изменения входных корней."""

    def setUp(self) -> None:
        """Готовит приёмочные документы на 20 из плана 50 и новые факты 10 / 4+6."""
        self.documents = document_fixture.StockTransferReceiptDocumentDomainTests()
        self.documents.setUp()
        self.model = self.documents.f
        self.d = self.documents.d
        self.time = self.documents.time
        self.reset_documents()
        self.issue = self.fact(self.issue_document, ("10",))
        self.receipt = self.fact(self.receipt_document, ("4", "6"))

    def reset_documents(self) -> None:
        """Строит и подтверждает обе стороны по текущему непринятому остатку, не создавая фактов."""
        self.documents.bindings = self.documents.new_bindings()
        self.documents.issue_document = self.documents.build()
        self.documents.receipt_document = self.documents.build(
            StockOperationType.RECEIPT
        )
        self.issue_document = self.documents.confirm(self.documents.issue_document)
        self.receipt_document = self.documents.confirm(
            self.documents.receipt_document,
            receipt_companion_document=self.issue_document.transfer_receipt_snapshot(),
        )

    def fact(
        self,
        document: StockDocument,
        amounts: tuple[str, ...],
        *,
        document_line_ids: tuple[StockDocumentLineIdVO, ...] | None = None,
        uom: str = "KG",
    ) -> StockExecution:
        """Создаёт реальное исполнение с текущей версией своего документа и явно выбранными строками плана."""
        issue = document.operation_type is StockOperationType.ISSUE
        dimensions = (
            self.d.transit_dimensions if issue else self.model.destination_dimensions
        )
        route = (
            IssueExecutionRouteVO(dimensions)
            if issue
            else ReceiptExecutionRouteVO(dimensions)
        )
        identifiers = (
            (document.lines[0].id,) * len(amounts)
            if document_line_ids is None
            else document_line_ids
        )
        return StockExecution.create(
            identifier=StockExecutionIdVO(uuid4()),
            document=document.execution_snapshot(),
            executed_at=self.time,
            warehouse=self.d.transit_warehouse if issue else self.d.f.destination,
            inventory_items=(self.d.f.item.execution_snapshot(),),
            locations=(
                self.d.transit_location if issue else self.model.destination_location,
            ),
            lines=tuple(
                StockExecutionLine.create(
                    identifier=StockExecutionLineIdVO(uuid4()),
                    document_line_id=identifier,
                    inventory_item=self.d.f.item.execution_snapshot(),
                    quantity=QuantityVO(Decimal(value)),
                    uom=UomCodeVO(uom),
                    route=route,
                )
                for identifier, value in zip(identifiers, amounts)
            ),
        )

    def build(self, **changes: object) -> StockTransferReceiptSnapshot:
        """Передаёт текущие состояния до фактов и полный баланс принятой истории без ручных назначений."""
        return StockTransferReceiptPolicy.build_receipt_from_documents(
            **(
                dict(
                    transfer=self.model.transfer.receipt_snapshot(),
                    balance=self.model.balance(),
                    issue_document=self.issue_document.transfer_receipt_snapshot(),
                    receipt_document=self.receipt_document.transfer_receipt_snapshot(),
                    issue=self.issue.transfer_document_snapshot(),
                    receipt=self.receipt.transfer_document_snapshot(),
                    transit_warehouse=self.d.transit_warehouse,
                    destination_warehouse=self.d.f.destination,
                    locations=(
                        self.d.transit_location,
                        self.model.destination_location,
                    ),
                )
                | changes
            )
        )

    def accept(self) -> StockTransferReceiptSnapshot:
        """Возвращает независимых кандидатов прежними методами корней и фиксирует историю только в тестовой модели."""
        result = self.build()
        issue = self.issue_document.register_execution(
            self.issue.snapshot_for_document(), updated_at=self.time
        )
        receipt = self.receipt_document.register_execution(
            self.receipt.snapshot_for_document(), updated_at=self.time
        )
        transfer = self.model.transfer.register_receipt(
            result, expected_version=self.model.transfer.version, updated_at=self.time
        )
        self.issue_document, self.receipt_document = issue, receipt
        self.model.transfer = transfer
        self.model.receipts += (result,)
        self.model.executions += (self.issue.transfer_snapshot(),)
        return result

    def send_more(self) -> None:
        """Добавляет принятую отправку ещё 30 в транзит, сохраняя прогресс приёмки и старые документы."""
        issue = self.d.fact(StockOperationType.ISSUE, ("30",))
        receipt = self.d.fact(StockOperationType.RECEIPT, ("30",))
        dispatch = self.d.build(
            transfer=self.model.transfer.dispatch_snapshot(),
            issue=issue.transfer_snapshot(),
            receipt=receipt.transfer_snapshot(),
            issue_bindings=self.d.bindings(issue),
            receipt_bindings=self.d.bindings(receipt),
        )
        self.model.transfer = self.d.register(dispatch, self.model.transfer)
        self.model.dispatches += (dispatch,)
        self.model.executions += (receipt.transfer_snapshot(),)

    def prepare_two_lines(self) -> None:
        """Готовит два обязательства одного товара и принятую отправку 8+12 с разными назначениями."""
        second = self.d.f.new_line()
        transfer = self.d.f.confirm(self.d.f.add(self.d.f.add(), second))
        issue = self.d.fact(StockOperationType.ISSUE, ("8", "12"))
        receipt = self.d.fact(StockOperationType.RECEIPT, ("8", "12"))
        dispatch = self.d.build(
            transfer=transfer.dispatch_snapshot(),
            issue=issue.transfer_snapshot(),
            receipt=receipt.transfer_snapshot(),
            issue_bindings=tuple(
                StockTransferExecutionBindingVO(fact.id, line_id)
                for fact, line_id in zip(issue.lines, (self.d.f.line.id, second.id))
            ),
            receipt_bindings=tuple(
                StockTransferExecutionBindingVO(fact.id, line_id)
                for fact, line_id in zip(receipt.lines, (self.d.f.line.id, second.id))
            ),
        )
        self.model.transfer = self.d.register(dispatch, transfer)
        self.model.dispatches, self.model.receipts, self.model.executions = (
            (dispatch,),
            (),
            (receipt.transfer_snapshot(),),
        )
        self.reset_documents()

    def test_automatic_result_equals_manual_receipt_and_keeps_inputs_unchanged(
        self,
    ) -> None:
        """Новая цепочка 10 / 4+6 даёт прежнюю регистрацию приёмки без переданных назначений."""
        automatic = self.build()
        manual = StockTransferReceiptPolicy.build_receipt(
            transfer=self.model.transfer.receipt_snapshot(),
            balance=self.model.balance(),
            issue=self.issue.transfer_snapshot(),
            receipt=self.receipt.transfer_snapshot(),
            transit_warehouse=self.d.transit_warehouse,
            destination_warehouse=self.d.f.destination,
            locations=(self.d.transit_location, self.model.destination_location),
            issue_bindings=self.model.bindings(self.issue),
            receipt_bindings=self.model.bindings(self.receipt),
        )
        self.assertEqual(automatic, manual)
        self.assertEqual(
            (
                automatic.lines[0].quantity.value,
                len(automatic.lines[0].issue_execution_line_ids),
                len(automatic.lines[0].receipt_execution_line_ids),
            ),
            (Decimal(10), 1, 2),
        )
        self.assertEqual(
            (
                self.model.transfer.version,
                self.issue_document.version,
                self.receipt_document.version,
            ),
            (3, 1, 1),
        )
        self.assertEqual(self.model.transfer.lines[0].received_qty.value, Decimal(0))

    def test_partial_receipts_keep_historical_basis_and_complete_documents_only(
        self,
    ) -> None:
        """Два факта по 10 завершают документы на 20, но сохраняют открытым план 50."""
        self.accept()
        self.assertEqual(
            (self.model.transfer.version, self.issue_document.version), (4, 2)
        )
        self.assertEqual(
            self.issue_document.status, StockDocumentStatus.PARTIALLY_EXECUTED
        )
        self.issue, self.receipt = self.fact(self.issue_document, ("10",)), self.fact(
            self.receipt_document, ("10",)
        )
        result = self.accept()
        self.assertEqual(result.transfer_version, 4)
        self.assertEqual(
            (self.issue_document.status, self.receipt_document.status),
            (StockDocumentStatus.COMPLETED, StockDocumentStatus.COMPLETED),
        )
        self.assertEqual(
            (self.issue_document.source.version, self.receipt_document.source.version),
            (3, 3),
        )
        self.assertEqual(
            (
                self.model.transfer.version,
                self.model.transfer.status,
                self.model.transfer.lines[0].received_qty.value,
            ),
            (5, StockTransferStatus.IN_PROGRESS, Decimal(20)),
        )
        self.assertEqual(
            self.model.transfer.lines[0].remaining_to_dispatch_qty().value, Decimal(30)
        )
        self.assertEqual(self.model.balance().lines, ())

    def test_additional_dispatch_does_not_expand_existing_document_limit(self) -> None:
        """При росте транзита до 40 старый документ допускает только оставшиеся 10, сохраняя основание v3."""
        self.accept()
        self.send_more()
        self.assertEqual(self.model.balance().lines[0].quantity.value, Decimal(40))
        self.issue, self.receipt = self.fact(self.issue_document, ("10",)), self.fact(
            self.receipt_document, ("10",)
        )
        result = self.accept()
        self.assertEqual(result.transfer_version, 5)
        self.assertEqual(self.issue_document.source.version, 3)
        self.assertEqual(
            (
                self.model.transfer.lines[0].dispatched_qty.value,
                self.model.transfer.lines[0].received_qty.value,
            ),
            (Decimal(50), Decimal(20)),
        )

    def test_stale_balance_is_rejected_even_with_valid_document_versions(self) -> None:
        """Баланс всегда относится к текущему перемещению, в отличие от исторического основания документов."""
        old = self.model.balance()
        self.accept()
        self.issue, self.receipt = self.fact(self.issue_document, ("10",)), self.fact(
            self.receipt_document, ("10",)
        )
        with self.assertRaises(StockTransferVersionConflictError):
            self.build(balance=old)

    def test_document_source_versions_must_match_and_cannot_be_from_future(
        self,
    ) -> None:
        """Отставание версии разрешено, разные основания сторон или будущая версия запрещены."""
        a, b = (
            self.issue_document.transfer_receipt_snapshot(),
            self.receipt_document.transfer_receipt_snapshot(),
        )
        with self.assertRaises(StockTransferVersionConflictError):
            self.build(receipt_document=replace(b, source_transfer_version=2))
        with self.assertRaises(StockTransferVersionConflictError):
            self.build(
                issue_document=replace(a, source_transfer_version=4),
                receipt_document=replace(b, source_transfer_version=4),
            )

    def test_current_versions_of_documents_are_independent_and_exact_for_each_fact(
        self,
    ) -> None:
        """Документы могут иметь разные собственные версии; каждый факт использует точную версию своей стороны."""
        b, fact = (
            self.receipt_document.transfer_receipt_snapshot(),
            self.receipt.transfer_document_snapshot(),
        )
        self.assertEqual(
            self.build(
                receipt_document=replace(b, version=7),
                receipt=replace(fact, document_version=7),
            )
            .lines[0]
            .quantity.value,
            Decimal(10),
        )
        with self.assertRaises(StaleStockDocumentVersionError):
            self.build(receipt=replace(fact, document_version=2))

    def test_pair_rejects_wrong_transfer_owner_roles_and_shared_identifiers(
        self,
    ) -> None:
        """Правильные количества не заменяют совпадение основания, владельца и ролей пары."""
        snapshot = self.receipt_document.transfer_receipt_snapshot()
        for changes in (
            dict(transfer_id=StockTransferIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(operation_type=StockOperationType.ISSUE),
            dict(id=self.issue_document.id),
        ):
            with self.assertRaises(StockTransferReceiptMismatchError):
                self.build(receipt_document=replace(snapshot, **changes))
        with self.assertRaises(StockTransferReceiptMismatchError):
            self.build(
                receipt_document=replace(
                    snapshot,
                    lines=(
                        replace(
                            snapshot.lines[0],
                            document_line_id=self.issue_document.lines[0].id,
                        ),
                    ),
                )
            )

    def test_pair_rejects_different_plans_and_accumulated_progress(self) -> None:
        """Сбалансированные новые факты не исправляют рассинхронизированные планы или прошлое исполнение."""
        snapshot = self.receipt_document.transfer_receipt_snapshot()
        with self.assertRaises(StockTransferReceiptMismatchError):
            self.build(
                receipt_document=replace(
                    snapshot,
                    lines=(
                        replace(snapshot.lines[0], planned_qty=QuantityVO(Decimal(15))),
                    ),
                )
            )
        self.accept()
        snapshot = self.receipt_document.transfer_receipt_snapshot()
        self.issue, self.receipt = self.fact(self.issue_document, ("5",)), self.fact(
            self.receipt_document, ("5",)
        )
        with self.assertRaises(StockTransferReceiptMismatchError):
            self.build(
                receipt_document=replace(
                    snapshot,
                    lines=(
                        replace(snapshot.lines[0], executed_qty=QuantityVO(Decimal(9))),
                    ),
                )
            )

    def test_document_and_fact_ids_scope_and_version_must_match(self) -> None:
        """Чужое документное основание, операция или склад не проходят общую проверку исполнения."""
        fact = self.issue.transfer_document_snapshot()
        for changes in (
            dict(document_id=StockDocumentIdVO(uuid4())),
            dict(operation_type=StockOperationType.RECEIPT),
            dict(warehouse_id=WarehouseIdVO(uuid4())),
        ):
            with self.assertRaises(InvalidStockDocumentContextError):
                self.build(issue=replace(fact, **changes))
        with self.assertRaises(StaleStockDocumentVersionError):
            self.build(issue=replace(fact, document_version=0))

    def test_document_limit_is_independent_of_available_transit(self) -> None:
        """Доступный транзит 20 не разрешает факт 10 в документе с планом 5."""
        a, b = (
            self.issue_document.transfer_receipt_snapshot(),
            self.receipt_document.transfer_receipt_snapshot(),
        )
        with self.assertRaises(StockDocumentOverExecutionError):
            self.build(
                issue_document=replace(
                    a, lines=(replace(a.lines[0], planned_qty=QuantityVO(Decimal(5))),)
                ),
                receipt_document=replace(
                    b, lines=(replace(b.lines[0], planned_qty=QuantityVO(Decimal(5))),)
                ),
            )

    def test_document_limit_sums_several_facts_of_one_line(self) -> None:
        """При плане 9 расход 8 проходит, но приход 4+6 превышает документ до проверки физического баланса."""
        self.issue = self.fact(self.issue_document, ("8",))
        a, b = (
            self.issue_document.transfer_receipt_snapshot(),
            self.receipt_document.transfer_receipt_snapshot(),
        )
        with self.assertRaises(StockDocumentOverExecutionError):
            self.build(
                issue_document=replace(
                    a, lines=(replace(a.lines[0], planned_qty=QuantityVO(Decimal(9))),)
                ),
                receipt_document=replace(
                    b, lines=(replace(b.lines[0], planned_qty=QuantityVO(Decimal(9))),)
                ),
            )

    def test_current_transit_limit_is_independent_of_unexecuted_document_plan(
        self,
    ) -> None:
        """Другой принятый факт уменьшает транзит: план 20 не разрешает новые 11 при остатке 10."""
        self.model.accept()
        self.issue, self.receipt = self.fact(self.issue_document, ("11",)), self.fact(
            self.receipt_document, ("11",)
        )
        with self.assertRaises(StockTransferTransitStockExceededError):
            self.build()

    def test_already_received_line_remains_known_when_receiving_another_line(
        self,
    ) -> None:
        """Полный снимок перемещения сохраняет основания уже принятых строк документа."""
        self.prepare_two_lines()
        first, second = self.documents.bindings
        for binding, value in ((first, "8"), (second, "12")):
            # Назначения идут в порядке строк StockTransfer, а не случайного порядка UUID документов.
            self.issue = self.fact(
                self.issue_document,
                (value,),
                document_line_ids=(binding.issue_document_line_id,),
            )
            self.receipt = self.fact(
                self.receipt_document,
                (value,),
                document_line_ids=(binding.receipt_document_line_id,),
            )
            self.accept()
        self.assertEqual(
            (self.issue_document.status, self.receipt_document.status),
            (StockDocumentStatus.COMPLETED, StockDocumentStatus.COMPLETED),
        )
        self.assertEqual(self.model.balance().lines, ())
        self.assertEqual(self.model.transfer.status, StockTransferStatus.IN_PROGRESS)

    def test_nonexecuted_lines_must_also_reference_known_transfer_item_and_unit(
        self,
    ) -> None:
        """Проверка не пропускает невыбранную новым фактом строку документа."""
        self.prepare_two_lines()
        first, second = self.documents.bindings
        self.issue = self.fact(
            self.issue_document,
            ("8",),
            document_line_ids=(first.issue_document_line_id,),
        )
        self.receipt = self.fact(
            self.receipt_document,
            ("8",),
            document_line_ids=(first.receipt_document_line_id,),
        )
        a, b = (
            self.issue_document.transfer_receipt_snapshot(),
            self.receipt_document.transfer_receipt_snapshot(),
        )
        for changes in (
            dict(transfer_line_id=StockTransferLineIdVO(uuid4())),
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
        ):

            def corrupt(
                snapshot: StockDocumentTransferReceiptSnapshot,
            ) -> StockDocumentTransferReceiptSnapshot:
                """Повреждает только вторую строку, которую текущий факт не исполняет."""
                return replace(
                    snapshot,
                    lines=tuple(
                        (
                            replace(line, **changes)
                            if line.transfer_line_id == second.transfer_line_id
                            else line
                        )
                        for line in snapshot.lines
                    ),
                )

            with self.assertRaises(StockTransferReceiptMismatchError):
                self.build(issue_document=corrupt(a), receipt_document=corrupt(b))

    def test_same_item_totals_cannot_reassign_receipt_between_obligations(self) -> None:
        """Одинаковый товар не разрешает расходить первое обязательство и приходовать второе."""
        self.prepare_two_lines()
        first, second = self.documents.bindings
        self.issue = self.fact(
            self.issue_document,
            ("8",),
            document_line_ids=(first.issue_document_line_id,),
        )
        self.receipt = self.fact(
            self.receipt_document,
            ("8",),
            document_line_ids=(second.receipt_document_line_id,),
        )
        with self.assertRaises(UnbalancedStockTransferReceiptError):
            self.build()

    def test_all_actual_lines_require_known_document_line_item_and_unit(self) -> None:
        """Ни один фактический ID не пропускается, товар и единица проверяются до группировки."""
        fact = self.issue.transfer_document_snapshot()
        row = fact.lines[0]
        other_item = InventoryItemIdVO(uuid4())
        for changed in (
            replace(row, document_line_id=StockDocumentLineIdVO(uuid4())),
            replace(row, base_uom=UomCodeVO("G")),
            replace(
                row,
                inventory_item_id=other_item,
                dimensions=replace(row.dimensions, inventory_item_id=other_item),
            ),
        ):
            with self.assertRaises(InvalidStockDocumentContextError):
                self.build(issue=replace(fact, lines=(changed,)))

    def test_specific_lot_and_stock_status_remain_conserved_and_available(self) -> None:
        """Документы на 20 не покрывают приёмку 10 из LOT A при остатках A=8/B=12."""
        balance = self.model.balance()
        row = balance.lines[0]
        a, b = StockLotIdVO(uuid4()), StockLotIdVO(uuid4())
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
        issue, receipt = (
            self.issue.transfer_document_snapshot(),
            self.receipt.transfer_document_snapshot(),
        )

        def with_lot(
            snapshot: StockExecutionTransferDocumentSnapshot, lot: StockLotIdVO
        ) -> StockExecutionTransferDocumentSnapshot:
            """Назначает сохраняемую партию всем фактическим строкам одной стороны."""
            return replace(
                snapshot,
                lines=tuple(
                    replace(line, dimensions=replace(line.dimensions, lot_id=lot))
                    for line in snapshot.lines
                ),
            )

        with self.assertRaises(StockTransferTransitStockExceededError):
            self.build(
                balance=balance, issue=with_lot(issue, a), receipt=with_lot(receipt, a)
            )
        self.assertEqual(
            self.build(
                balance=balance, issue=with_lot(issue, b), receipt=with_lot(receipt, b)
            )
            .lines[0]
            .quantity.value,
            Decimal(10),
        )
        with self.assertRaises(UnbalancedStockTransferReceiptError):
            self.build(
                balance=balance, issue=with_lot(issue, a), receipt=with_lot(receipt, b)
            )
        with self.assertRaises(UnbalancedStockTransferReceiptError):
            self.build(
                receipt=replace(
                    receipt,
                    lines=tuple(
                        replace(
                            line,
                            dimensions=replace(
                                line.dimensions, stock_status=StockStatus.DAMAGED
                            ),
                        )
                        for line in receipt.lines
                    ),
                )
            )

    def test_specific_serial_cannot_be_replaced_or_covered_by_another_instance(
        self,
    ) -> None:
        """В PCS приёмка требует ту же серию на обеих сторонах и её наличие в текущем балансе."""
        serial, other = StockSerialIdVO(uuid4()), StockSerialIdVO(uuid4())
        plan = self.model.transfer.receipt_snapshot()
        plan = replace(
            plan,
            lines=(
                replace(
                    plan.lines[0],
                    base_uom=UomCodeVO("PCS"),
                    dispatched_qty=QuantityVO(Decimal(2)),
                ),
            ),
        )
        balance = self.model.balance()
        row = balance.lines[0]
        balance = replace(
            balance,
            lines=tuple(
                replace(
                    row,
                    base_uom=UomCodeVO("PCS"),
                    quantity=QuantityVO(Decimal(1)),
                    dimensions=replace(row.dimensions, serial_id=value),
                )
                for value in (serial, other)
            ),
        )
        a, b = (
            self.issue_document.transfer_receipt_snapshot(),
            self.receipt_document.transfer_receipt_snapshot(),
        )
        a, b = replace(
            a,
            lines=(
                replace(
                    a.lines[0],
                    base_uom=UomCodeVO("PCS"),
                    planned_qty=QuantityVO(Decimal(2)),
                ),
            ),
        ), replace(
            b,
            lines=(
                replace(
                    b.lines[0],
                    base_uom=UomCodeVO("PCS"),
                    planned_qty=QuantityVO(Decimal(2)),
                ),
            ),
        )
        issue, receipt = (
            self.issue.transfer_document_snapshot(),
            self.receipt.transfer_document_snapshot(),
        )
        issue = replace(
            issue,
            lines=(
                replace(
                    issue.lines[0],
                    base_uom=UomCodeVO("PCS"),
                    quantity=QuantityVO(Decimal(1)),
                    dimensions=replace(issue.lines[0].dimensions, serial_id=serial),
                ),
            ),
        )
        receipt = replace(
            receipt,
            lines=(
                replace(
                    receipt.lines[0],
                    base_uom=UomCodeVO("PCS"),
                    quantity=QuantityVO(Decimal(1)),
                    dimensions=replace(receipt.lines[0].dimensions, serial_id=serial),
                ),
            ),
        )
        arguments = dict(
            transfer=plan,
            balance=balance,
            issue_document=a,
            receipt_document=b,
            issue=issue,
            receipt=receipt,
        )
        self.assertEqual(self.build(**arguments).lines[0].quantity.value, Decimal(1))
        with self.assertRaises(UnbalancedStockTransferReceiptError):
            self.build(
                **(
                    arguments
                    | dict(
                        receipt=replace(
                            receipt,
                            lines=(
                                replace(
                                    receipt.lines[0],
                                    dimensions=replace(
                                        receipt.lines[0].dimensions, serial_id=other
                                    ),
                                ),
                            ),
                        )
                    )
                )
            )
        missing = StockSerialIdVO(uuid4())
        with self.assertRaises(StockTransferTransitStockExceededError):
            self.build(
                **(
                    arguments
                    | dict(
                        issue=replace(
                            issue,
                            lines=(
                                replace(
                                    issue.lines[0],
                                    dimensions=replace(
                                        issue.lines[0].dimensions, serial_id=missing
                                    ),
                                ),
                            ),
                        ),
                        receipt=replace(
                            receipt,
                            lines=(
                                replace(
                                    receipt.lines[0],
                                    dimensions=replace(
                                        receipt.lines[0].dimensions, serial_id=missing
                                    ),
                                ),
                            ),
                        ),
                    )
                )
            )

    def test_new_pair_cannot_reuse_facts_already_present_in_accepted_history(
        self,
    ) -> None:
        """Даже подмена версии старых фактов на текущую документную не обходит проверку ID принятой истории."""
        self.accept()
        with self.assertRaises(StaleStockDocumentVersionError):
            self.build()
        with self.assertRaises(StockTransferReceiptMismatchError):
            self.build(
                issue=replace(
                    self.issue.transfer_document_snapshot(),
                    document_version=self.issue_document.version,
                ),
                receipt=replace(
                    self.receipt.transfer_document_snapshot(),
                    document_version=self.receipt_document.version,
                ),
            )

    def test_warehouse_a_is_not_required_but_t_and_b_must_be_active(self) -> None:
        """Деактивация A не мешает приёмке; активность T/B проверяется прежней физической политикой."""
        self.d.f.source = replace(self.d.f.source, is_active=False)
        self.assertEqual(self.build().lines[0].quantity.value, Decimal(10))
        for name, warehouse in (
            ("transit_warehouse", self.d.transit_warehouse),
            ("destination_warehouse", self.d.f.destination),
        ):
            with self.assertRaises(WarehouseInactiveError):
                self.build(**{name: replace(warehouse, is_active=False)})
        with self.assertRaises(InventoryError):
            self.build(
                locations=(
                    replace(
                        self.d.transit_location, location_type=LocationType.STORAGE
                    ),
                    self.model.destination_location,
                )
            )

    def test_fact_and_document_matching_wrong_warehouse_still_cannot_change_route(
        self,
    ) -> None:
        """Совпадение ложного склада у документа и факта не меняет зафиксированный маршрут T → B."""
        wrong = WarehouseIdVO(uuid4())
        with self.assertRaises(StockTransferReceiptMismatchError):
            self.build(
                receipt_document=replace(
                    self.receipt_document.transfer_receipt_snapshot(),
                    warehouse_id=wrong,
                ),
                receipt=replace(
                    self.receipt.transfer_document_snapshot(), warehouse_id=wrong
                ),
            )

    def test_times_cover_documents_current_transfer_and_equal_fact_time(self) -> None:
        """Факты должны быть не раньше своих документов и перемещения, с одним временем на обе стороны."""
        issue, receipt = (
            self.issue.transfer_document_snapshot(),
            self.receipt.transfer_document_snapshot(),
        )
        early = self.time - timedelta(seconds=1)
        with self.assertRaises(StockExecutionTimeError):
            self.build(
                issue=replace(issue, executed_at=early),
                receipt=replace(receipt, executed_at=early),
            )
        with self.assertRaises(StockTransferTimeError):
            self.build(
                receipt=replace(receipt, executed_at=self.time + timedelta(seconds=1))
            )
        with self.assertRaises(StockTransferTimeError):
            self.build(
                transfer=replace(
                    self.model.transfer.receipt_snapshot(),
                    updated_at=self.time + timedelta(seconds=1),
                )
            )

    def test_document_states_and_transfer_status_are_checked(self) -> None:
        """Черновые, отменённые или завершённые документы и неисполняемое перемещение запрещены."""
        for document in (
            self.documents.issue_document,
            self.issue_document.cancel(updated_at=self.time),
        ):
            with self.assertRaises(StockDocumentExecutionNotAllowedError):
                self.build(issue_document=document.transfer_receipt_snapshot())
        with self.assertRaises(StockTransferStatusError):
            self.build(transfer=self.d.transfer.receipt_snapshot())
        self.issue, self.receipt = self.fact(self.issue_document, ("20",)), self.fact(
            self.receipt_document, ("20",)
        )
        self.accept()
        with self.assertRaises(StockDocumentExecutionNotAllowedError):
            self.build()

    def test_runtime_types_reject_wrong_stage_snapshots_and_raw_roots(self) -> None:
        """Номинальные снимки этапов не взаимозаменяемы; данные полных корней не используются как контракт."""
        for key, value in (
            ("transfer", self.model.transfer),
            ("issue_document", self.issue_document),
            ("issue", self.issue),
            ("balance", None),
        ):
            with self.assertRaises(InventoryError):
                self.build(**{key: value})
        receipt = self.receipt_document.transfer_receipt_snapshot()
        wrong_stage = StockDocumentTransferDispatchSnapshot(
            *(getattr(receipt, name) for name in receipt.__dataclass_fields__)
        )
        with self.assertRaises(InvalidStockDocumentTransferReceiptSnapshotError):
            self.build(receipt_document=wrong_stage)

    def test_runtime_validation_checks_versions_and_duplicates(self) -> None:
        """Сырые dataclass не обходят строгие версии, типы строк и уникальность фактических ID."""
        fact = self.issue.transfer_document_snapshot()
        for changes in (
            dict(document_version=True),
            dict(document_id=uuid4()),
            dict(lines=()),
            dict(lines=(fact.lines[0], fact.lines[0])),
        ):
            with self.assertRaises(InventoryError):
                self.build(issue=replace(fact, **changes))
        with self.assertRaises(StockTransferReceiptMismatchError):
            self.build(
                receipt=replace(
                    self.receipt.transfer_document_snapshot(), id=self.issue.id
                )
            )

    def test_shared_policy_direct_calls_validate_inputs_and_build_all_bindings(
        self,
    ) -> None:
        """Общая политика независимо проверяет контракты и связывает каждый факт с основанием своей строки."""
        result = StockTransferDocumentExecutionPolicy.build_bindings(
            document=self.issue_document.transfer_receipt_snapshot(),
            execution=self.issue.transfer_document_snapshot(),
        )
        self.assertEqual(result, self.model.bindings(self.issue))
        for document, execution in (
            (self.issue_document, self.issue.transfer_document_snapshot()),
            (self.issue_document.transfer_receipt_snapshot(), self.issue),
        ):
            with self.assertRaises(InventoryError):
                StockTransferDocumentExecutionPolicy.build_bindings(
                    document=document, execution=execution
                )

    def test_hostile_decimal_context_and_fact_order_do_not_change_result(self) -> None:
        """Пересчёт G, сумма 4+6 и проверка обоих остатков точны при внешней точности 1."""
        self.issue = self.fact(self.issue_document, ("10000",), uom="G")
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            expected = self.build()
            snapshot = self.receipt.transfer_document_snapshot()
            self.assertEqual(
                self.build(
                    receipt=replace(snapshot, lines=tuple(reversed(snapshot.lines)))
                ),
                expected,
            )
            self.accept()
            self.assertEqual(
                self.model.transfer.lines[0].received_qty.value, Decimal(10)
            )

    def test_full_receipt_uses_existing_postings_and_completes_full_transfer(
        self,
    ) -> None:
        """После отправки 50 приёмки 20+30 сохраняют общий запас, завершают оба документа и StockTransfer."""
        self.send_more()
        self.reset_documents()
        transit = replace(self.d.transit_position, on_hand_qty=QuantityVO(Decimal(50)))
        destination = replace(
            self.d.transit_position,
            id=StockPositionIdVO(uuid4()),
            dimensions=self.model.destination_dimensions,
        )
        for value, incoming in (("20", ("8", "12")), ("30", ("30",))):
            self.issue, self.receipt = self.fact(
                self.issue_document, (value,)
            ), self.fact(self.receipt_document, incoming)
            outgoing = self.d.posting(self.issue, transit, self.d.transit_location)
            incoming_posting = self.d.posting(
                self.receipt, destination, self.model.destination_location
            )
            self.assertEqual(outgoing.posted_at, incoming_posting.posted_at)
            transit = transit.apply_posting_entry(
                outgoing.entries[0].snapshot(),
                expected_version=transit.version,
                inventory_item=self.d.f.item.stock_snapshot(),
                location=self.d.transit_location,
                warehouse=self.d.transit_warehouse,
            )
            destination = destination.apply_posting_entry(
                incoming_posting.entries[0].snapshot(),
                expected_version=destination.version,
                inventory_item=self.d.f.item.stock_snapshot(),
                location=self.model.destination_location,
                warehouse=self.d.f.destination,
            )
            self.accept()
            self.assertEqual(
                transit.on_hand_qty.value + destination.on_hand_qty.value, Decimal(50)
            )
        self.assertEqual(
            (transit.on_hand_qty.value, destination.on_hand_qty.value),
            (Decimal(0), Decimal(50)),
        )
        self.assertEqual(
            (self.model.transfer.version, self.model.transfer.status),
            (6, StockTransferStatus.COMPLETED),
        )
        self.assertEqual(
            (self.issue_document.status, self.receipt_document.status),
            (StockDocumentStatus.COMPLETED, StockDocumentStatus.COMPLETED),
        )
        self.assertEqual(self.issue_document.source.version, 4)
        self.assertEqual(self.model.balance().lines, ())
        with self.assertRaises(StockTransferStatusError):
            self.build()


if __name__ == "__main__":
    unittest.main()
