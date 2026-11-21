"""Автоматическая регистрация отправки по двум документам: связи, лимиты, версии и сохраняемый состав."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_stock_transfer_document_domain as document_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.stock_transfer_dispatch import (
    StockTransferDispatchPolicy,
)
from src.modules.inventory.domain.stock_document.transfer_dispatch_snapshot import (
    StockDocumentTransferDispatchSnapshot,
)
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.error import (
    InvalidStockDocumentContextError,
    StockDocumentExecutionNotAllowedError,
    StockDocumentOverExecutionError,
    StaleStockDocumentVersionError,
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
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionTransferDocumentSnapshotError,
    StockExecutionTimeError,
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
from src.modules.inventory.domain.stock_execution.value_object.internal_move_route import (
    InternalMoveExecutionRouteVO,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_transfer.dispatch_snapshot import (
    StockTransferDispatchSnapshot,
)
from src.modules.inventory.domain.stock_transfer.error import (
    StockTransferDispatchMismatchError,
    StockTransferDispatchQuantityExceededError,
    StockTransferVersionConflictError,
    StockTransferTimeError,
    UnbalancedStockTransferDispatchError,
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
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.warehouse.error import WarehouseInactiveError


class StockTransferDocumentExecutionDomainTests(unittest.TestCase):
    """Проверяет автоматический путь без ручных назначений и изменения входных корней."""

    def setUp(self) -> None:
        """Готовит два подтверждённых плана по 50 KG и новую фактическую отправку 20 / 8+12."""
        self.f = document_fixture.StockTransferDocumentDomainTests()
        self.f.setUp()
        self.d = self.f.d
        self.time = self.f.time
        self.prepare_pair()

    def prepare_pair(self) -> None:
        """Подтверждает обе стороны по текущему основанию тестовой модели документов."""
        self.transfer = self.f.transfer
        self.issue_document = self.f.confirm(self.f.issue)
        self.receipt_document = self.f.confirm(
            self.f.receipt,
            companion_document=self.issue_document.transfer_dispatch_snapshot(),
        )
        binding = next(
            row for row in self.f.bindings if row.transfer_line_id == self.d.f.line.id
        )
        self.issue = self.fact(
            self.issue_document,
            ("20",),
            document_line_ids=(binding.issue_document_line_id,),
        )
        self.receipt = self.fact(
            self.receipt_document,
            ("8", "12"),
            document_line_ids=(
                binding.receipt_document_line_id,
                binding.receipt_document_line_id,
            ),
        )

    def fact(
        self,
        document: StockDocument,
        amounts: tuple[str, ...],
        *,
        document_line_ids: tuple[StockDocumentLineIdVO, ...] | None = None,
        uom: str = "KG",
    ) -> StockExecution:
        """Создаёт полноценный факт существующим API с реальными ссылками на строки документа."""
        issue = document.operation_type is StockOperationType.ISSUE
        dimensions = self.d.source_dimensions if issue else self.d.transit_dimensions
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
            warehouse=self.d.f.source if issue else self.d.transit_warehouse,
            inventory_items=(self.d.f.item.execution_snapshot(),),
            locations=(self.d.source_location if issue else self.d.transit_location,),
            lines=tuple(
                StockExecutionLine.create(
                    identifier=StockExecutionLineIdVO(uuid4()),
                    document_line_id=identifier,
                    inventory_item=self.d.f.item.execution_snapshot(),
                    quantity=QuantityVO(Decimal(amount)),
                    uom=UomCodeVO(uom),
                    route=route,
                )
                for identifier, amount in zip(identifiers, amounts)
            ),
        )

    def build(self, **changes: object) -> StockTransferDispatchSnapshot:
        """Передаёт свежие снимки перед регистрацией фактов, не предоставляя ручных назначений."""
        return StockTransferDispatchPolicy.build_dispatch_from_documents(
            **(
                dict(
                    transfer=self.transfer.dispatch_snapshot(),
                    issue_document=self.issue_document.transfer_dispatch_snapshot(),
                    receipt_document=self.receipt_document.transfer_dispatch_snapshot(),
                    issue=self.issue.transfer_document_snapshot(),
                    receipt=self.receipt.transfer_document_snapshot(),
                    transit=self.d.transit,
                    source_warehouse=self.d.f.source,
                    destination_warehouse=self.d.f.destination,
                    transit_warehouse=self.d.transit_warehouse,
                    locations=(self.d.source_location, self.d.transit_location),
                )
                | changes
            )
        )

    def accept(self) -> StockTransferDispatchSnapshot:
        """Строит независимых кандидатов обоих документов и перемещения, затем сохраняет их в тестовой модели."""
        dispatch = self.build()
        transfer = self.transfer.register_dispatch(
            dispatch, expected_version=self.transfer.version, updated_at=self.time
        )
        issue = self.issue_document.register_execution(
            self.issue.snapshot_for_document(), updated_at=self.time
        )
        receipt = self.receipt_document.register_execution(
            self.receipt.snapshot_for_document(), updated_at=self.time
        )
        self.transfer, self.issue_document, self.receipt_document = (
            transfer,
            issue,
            receipt,
        )
        return dispatch

    def add_second_line(self, quantity: str = "50") -> None:
        """Готовит два обязательства одного товара, не объединяемые при построении документов."""
        second = self.d.f.new_line(quantity=QuantityVO(Decimal(quantity)))
        self.f.transfer = self.d.f.confirm(self.d.f.add(self.d.f.add(), second))
        self.f.bindings = self.f.new_bindings()
        self.f.issue, self.f.receipt = self.f.build(), self.f.build(
            StockOperationType.RECEIPT
        )
        self.prepare_pair()

    def test_automatic_dispatch_equals_existing_manual_result_for_split_receipt(
        self,
    ) -> None:
        """Расход 20 и приход 8+12 дают тот же результат, что прежние явно заданные назначения."""
        automatic = self.build()
        manual = self.d.build(
            transfer=self.transfer.dispatch_snapshot(),
            issue=self.issue.transfer_snapshot(),
            receipt=self.receipt.transfer_snapshot(),
            issue_bindings=self.d.bindings(self.issue),
            receipt_bindings=self.d.bindings(self.receipt),
        )
        self.assertEqual(automatic, manual)
        self.assertEqual(
            (
                automatic.lines[0].quantity.value,
                len(automatic.lines[0].issue_execution_line_ids),
                len(automatic.lines[0].receipt_execution_line_ids),
            ),
            (Decimal(20), 1, 2),
        )
        self.assertEqual(
            (
                self.transfer.version,
                self.issue_document.version,
                self.receipt_document.version,
            ),
            (2, 1, 1),
        )
        self.assertEqual(self.transfer.lines[0].dispatched_qty.value, Decimal(0))

    def test_new_snapshot_preserves_document_refs_and_existing_physical_profile(
        self,
    ) -> None:
        """Новый контракт сохраняет полную связь с документом и проецируется в неизменённый физический снимок."""
        snapshot = self.receipt.transfer_document_snapshot()
        self.assertEqual(
            (snapshot.document_id, snapshot.document_version),
            (self.receipt_document.id, 1),
        )
        self.assertEqual(
            {row.document_line_id for row in snapshot.lines},
            {self.receipt_document.lines[0].id},
        )
        self.assertEqual(snapshot.transfer_snapshot(), self.receipt.transfer_snapshot())
        self.assertEqual(snapshot.lines[0].dimensions, self.d.transit_dimensions)
        with self.assertRaises(FrozenInstanceError):
            snapshot.document_version = 2

    def test_partial_facts_keep_historical_source_and_use_current_document_versions(
        self,
    ) -> None:
        """20, затем 30 завершают документы; source.version=2 не мешает отправке по StockTransfer v3."""
        first = self.accept()
        self.assertEqual(first.transfer_version, 2)
        self.assertEqual((self.transfer.version, self.issue_document.version), (3, 2))
        self.assertEqual(
            self.issue_document.status, StockDocumentStatus.PARTIALLY_EXECUTED
        )
        self.issue, self.receipt = self.fact(self.issue_document, ("30",)), self.fact(
            self.receipt_document, ("30",)
        )
        second = self.accept()
        self.assertEqual(second.transfer_version, 3)
        self.assertEqual(
            (self.issue_document.status, self.receipt_document.status),
            (StockDocumentStatus.COMPLETED, StockDocumentStatus.COMPLETED),
        )
        self.assertEqual(
            (self.issue_document.source.version, self.receipt_document.source.version),
            (2, 2),
        )
        self.assertEqual(
            (
                self.transfer.version,
                self.transfer.status,
                self.transfer.lines[0].dispatched_qty.value,
                self.transfer.lines[0].received_qty.value,
            ),
            (4, StockTransferStatus.IN_PROGRESS, Decimal(50), Decimal(0)),
        )

    def test_receipt_progress_between_dispatches_keeps_historical_document_basis_valid(
        self,
    ) -> None:
        """Приёмка части транзита меняет версию перемещения, но не основания уже подтверждённых документов отправки."""
        self.accept()
        # Историческое состояние после принятой приёмки 10 из отправленных 20.
        self.transfer = self.d.restore(
            self.transfer,
            version=4,
            lines=(
                replace(self.transfer.lines[0], received_qty=QuantityVO(Decimal(10))),
            ),
        )
        self.issue = self.fact(self.issue_document, ("30",))
        self.receipt = self.fact(self.receipt_document, ("30",))
        result = self.accept()
        self.assertEqual(result.transfer_version, 4)
        self.assertEqual(self.issue_document.source.version, 2)
        self.assertEqual(
            (
                self.transfer.lines[0].dispatched_qty.value,
                self.transfer.lines[0].received_qty.value,
            ),
            (Decimal(50), Decimal(10)),
        )
        self.assertEqual(self.transfer.status, StockTransferStatus.IN_PROGRESS)

    def test_current_document_versions_may_differ_between_sides(self) -> None:
        """Важна точная версия своей стороны, равенство собственных версий двух документов не требуется."""
        document = replace(
            self.receipt_document.transfer_dispatch_snapshot(), version=7
        )
        execution = replace(
            self.receipt.transfer_document_snapshot(), document_version=7
        )
        self.assertEqual(
            self.build(receipt_document=document, receipt=execution)
            .lines[0]
            .quantity.value,
            Decimal(20),
        )

    def test_reusing_states_after_registration_rejects_old_fact_version(self) -> None:
        """Политике нужны оба состояния до факта; после регистрации исполнения версии уже другие."""
        self.accept()
        with self.assertRaises(StaleStockDocumentVersionError):
            self.build()

    def test_source_versions_must_match_each_other_and_cannot_come_from_future(
        self,
    ) -> None:
        """Историческое основание допускается, но две стороны не могут иметь разные версии или версию из будущего."""
        a, t = (
            self.issue_document.transfer_dispatch_snapshot(),
            self.receipt_document.transfer_dispatch_snapshot(),
        )
        with self.assertRaises(StockTransferVersionConflictError):
            self.build(receipt_document=replace(t, source_transfer_version=1))
        with self.assertRaises(StockTransferVersionConflictError):
            self.build(
                issue_document=replace(a, source_transfer_version=3),
                receipt_document=replace(t, source_transfer_version=3),
            )

    def test_document_pair_requires_same_transfer_owner_roles_and_different_ids(
        self,
    ) -> None:
        """Чужое основание/владелец, два расхода и один ID документа не образуют пару отправки."""
        snapshot = self.receipt_document.transfer_dispatch_snapshot()
        for changes in (
            dict(transfer_id=StockTransferIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(operation_type=StockOperationType.ISSUE),
            dict(id=self.issue_document.id),
        ):
            with self.assertRaises(StockTransferDispatchMismatchError):
                self.build(receipt_document=replace(snapshot, **changes))
        with self.assertRaises(StockTransferDispatchMismatchError):
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

    def test_pair_rejects_different_plans_even_when_new_facts_balance(self) -> None:
        """Сбалансированные факты 20/20 не скрывают несовместимые планы документов 50/40."""
        snapshot = self.receipt_document.transfer_dispatch_snapshot()
        with self.assertRaises(StockTransferDispatchMismatchError):
            self.build(
                receipt_document=replace(
                    snapshot,
                    lines=(
                        replace(snapshot.lines[0], planned_qty=QuantityVO(Decimal(40))),
                    ),
                )
            )

    def test_pair_rejects_different_accumulated_progress(self) -> None:
        """Согласованная отправка требует одинаковый накопленный прогресс парных обязательств до нового факта."""
        self.accept()
        self.issue, self.receipt = self.fact(self.issue_document, ("10",)), self.fact(
            self.receipt_document, ("10",)
        )
        snapshot = self.receipt_document.transfer_dispatch_snapshot()
        with self.assertRaises(StockTransferDispatchMismatchError):
            self.build(
                receipt_document=replace(
                    snapshot,
                    lines=(
                        replace(
                            snapshot.lines[0], executed_qty=QuantityVO(Decimal(19))
                        ),
                    ),
                )
            )

    def test_document_and_fact_scope_and_exact_versions_are_required(self) -> None:
        """Документ и факт совпадают по ID, версии, операции, складу и владельцу."""
        snapshot = self.issue.transfer_document_snapshot()
        for changes in (
            dict(document_id=StockDocumentIdVO(uuid4())),
            dict(operation_type=StockOperationType.RECEIPT),
            dict(warehouse_id=WarehouseIdVO(uuid4())),
        ):
            with self.assertRaises(InvalidStockDocumentContextError):
                self.build(issue=replace(snapshot, **changes))
        for version in (0, 2):
            with self.assertRaises(StaleStockDocumentVersionError):
                self.build(issue=replace(snapshot, document_version=version))

    def test_document_states_must_be_confirmed_or_partially_executed(self) -> None:
        """Черновики и отменённые документы не допускаются, даже если фактические количества допустимы."""
        for document in (
            self.f.issue,
            self.issue_document.cancel(updated_at=self.time),
        ):
            with self.assertRaises(StockDocumentExecutionNotAllowedError):
                self.build(issue_document=document.transfer_dispatch_snapshot())
        self.issue, self.receipt = self.fact(self.issue_document, ("50",)), self.fact(
            self.receipt_document, ("50",)
        )
        self.accept()
        with self.assertRaises(StockDocumentExecutionNotAllowedError):
            self.build()

    def test_all_fact_lines_require_known_document_line_and_matching_item_unit(
        self,
    ) -> None:
        """Ни одна фактическая строка не пропускается; товар и единица проверяются до суммирования."""
        snapshot = self.issue.transfer_document_snapshot()
        row = snapshot.lines[0]
        changed_item = InventoryItemIdVO(uuid4())
        for changed in (
            replace(row, document_line_id=StockDocumentLineIdVO(uuid4())),
            replace(row, base_uom=UomCodeVO("G")),
            replace(
                row,
                inventory_item_id=changed_item,
                dimensions=replace(row.dimensions, inventory_item_id=changed_item),
            ),
        ):
            with self.assertRaises(InvalidStockDocumentContextError):
                self.build(issue=replace(snapshot, lines=(changed,)))

    def test_document_limit_is_checked_before_transfer_limit(self) -> None:
        """Даже при остатке перемещения 50 факт 20 не проходит через документ с планом 10."""
        a, t = (
            self.issue_document.transfer_dispatch_snapshot(),
            self.receipt_document.transfer_dispatch_snapshot(),
        )
        with self.assertRaises(StockDocumentOverExecutionError):
            self.build(
                issue_document=replace(
                    a, lines=(replace(a.lines[0], planned_qty=QuantityVO(Decimal(10))),)
                ),
                receipt_document=replace(
                    t, lines=(replace(t.lines[0], planned_qty=QuantityVO(Decimal(10))),)
                ),
            )

    def test_document_limit_uses_sum_of_multiple_facts_for_one_plan_line(self) -> None:
        """При плане 15 расход 12 допустим, но приход 8+8 превышает документ до проверки физического баланса."""
        self.issue, self.receipt = self.fact(self.issue_document, ("12",)), self.fact(
            self.receipt_document, ("8", "8")
        )
        a, t = (
            self.issue_document.transfer_dispatch_snapshot(),
            self.receipt_document.transfer_dispatch_snapshot(),
        )
        with self.assertRaises(StockDocumentOverExecutionError):
            self.build(
                issue_document=replace(
                    a, lines=(replace(a.lines[0], planned_qty=QuantityVO(Decimal(15))),)
                ),
                receipt_document=replace(
                    t, lines=(replace(t.lines[0], planned_qty=QuantityVO(Decimal(15))),)
                ),
            )

    def test_current_transfer_remaining_is_independent_of_document_remaining(
        self,
    ) -> None:
        """Документный остаток 50 не позволяет отправить 20, когда по перемещению осталось только 5."""
        line = replace(self.transfer.lines[0], dispatched_qty=QuantityVO(Decimal(45)))
        self.transfer = self.d.restore(
            self.transfer,
            status=StockTransferStatus.IN_PROGRESS,
            transit=self.d.transit,
            lines=(line,),
            version=3,
        )
        with self.assertRaises(StockTransferDispatchQuantityExceededError):
            self.build()

    def test_completed_transfer_line_remains_known_during_execution_of_another_line(
        self,
    ) -> None:
        """Полный снимок перемещения сохраняет законченную строку документа при отправке остатка другой строки."""
        self.add_second_line("10")
        first_binding = next(
            row for row in self.f.bindings if row.transfer_line_id == self.d.f.line.id
        )
        second_binding = next(
            row for row in self.f.bindings if row.transfer_line_id != self.d.f.line.id
        )
        self.issue = self.fact(
            self.issue_document,
            ("50",),
            document_line_ids=(first_binding.issue_document_line_id,),
        )
        self.receipt = self.fact(
            self.receipt_document,
            ("50",),
            document_line_ids=(first_binding.receipt_document_line_id,),
        )
        self.accept()
        self.assertEqual(len(self.transfer.dispatch_document_snapshot().lines), 1)
        self.issue = self.fact(
            self.issue_document,
            ("10",),
            document_line_ids=(second_binding.issue_document_line_id,),
        )
        self.receipt = self.fact(
            self.receipt_document,
            ("10",),
            document_line_ids=(second_binding.receipt_document_line_id,),
        )
        self.accept()
        self.assertEqual(self.issue_document.status, StockDocumentStatus.COMPLETED)
        self.assertTrue(
            all(line.dispatched_qty == line.planned_qty for line in self.transfer.lines)
        )

    def test_nonexecuted_document_lines_also_require_known_transfer_item_and_uom(
        self,
    ) -> None:
        """Проверка охватывает и строки документа, для которых новый факт не передан."""
        self.add_second_line()
        executed_ref = self.issue_document.get_line(
            self.issue.lines[0].document_line_id
        ).source.reference
        other_ref = next(
            line.source.reference
            for line in self.issue_document.lines
            if line.source.reference != executed_ref
        )
        a, t = (
            self.issue_document.transfer_dispatch_snapshot(),
            self.receipt_document.transfer_dispatch_snapshot(),
        )
        unknown = StockTransferLineIdVO(uuid4())
        for changes in (
            dict(transfer_line_id=unknown),
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
        ):

            def corrupt(
                snapshot: StockDocumentTransferDispatchSnapshot,
            ) -> StockDocumentTransferDispatchSnapshot:
                """Повреждает только неисполняемую строку для проверки полного состава документа."""
                return replace(
                    snapshot,
                    lines=tuple(
                        (
                            replace(line, **changes)
                            if str(line.transfer_line_id.uuid) == other_ref
                            else line
                        )
                        for line in snapshot.lines
                    ),
                )

            with self.assertRaises(StockTransferDispatchMismatchError):
                self.build(issue_document=corrupt(a), receipt_document=corrupt(t))

    def test_equal_item_totals_cannot_move_facts_between_transfer_lines(self) -> None:
        """Два обязательства одного товара не позволяют назначить приход другой строке плана."""
        self.add_second_line()
        first, second = self.f.bindings
        self.issue = self.fact(
            self.issue_document,
            ("20",),
            document_line_ids=(first.issue_document_line_id,),
        )
        self.receipt = self.fact(
            self.receipt_document,
            ("20",),
            document_line_ids=(second.receipt_document_line_id,),
        )
        with self.assertRaises(UnbalancedStockTransferDispatchError):
            self.build()

    def test_lot_and_status_are_preserved_after_automatic_mapping(self) -> None:
        """Автоматические связи не отменяют физический баланс LOT и состояния обеих сторон."""
        issue, receipt = (
            self.issue.transfer_document_snapshot(),
            self.receipt.transfer_document_snapshot(),
        )
        lot = StockLotIdVO(uuid4())
        outgoing = replace(
            issue,
            lines=tuple(
                replace(line, dimensions=replace(line.dimensions, lot_id=lot))
                for line in issue.lines
            ),
        )
        incoming = replace(
            receipt,
            lines=tuple(
                replace(line, dimensions=replace(line.dimensions, lot_id=lot))
                for line in receipt.lines
            ),
        )
        self.assertEqual(
            self.build(issue=outgoing, receipt=incoming).lines[0].quantity.value,
            Decimal(20),
        )
        with self.assertRaises(UnbalancedStockTransferDispatchError):
            self.build(issue=outgoing)
        with self.assertRaises(UnbalancedStockTransferDispatchError):
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

    def test_serial_identity_and_unit_quantity_are_preserved(self) -> None:
        """Факты серийного товара требуют 1 PCS и ту же конкретную серию на обеих сторонах."""
        serial = StockSerialIdVO(uuid4())
        plan = self.transfer.dispatch_snapshot()
        plan = replace(plan, lines=(replace(plan.lines[0], base_uom=UomCodeVO("PCS")),))
        a, t = (
            self.issue_document.transfer_dispatch_snapshot(),
            self.receipt_document.transfer_dispatch_snapshot(),
        )
        a, t = replace(
            a, lines=(replace(a.lines[0], base_uom=UomCodeVO("PCS")),)
        ), replace(t, lines=(replace(t.lines[0], base_uom=UomCodeVO("PCS")),))
        issue, receipt = (
            self.issue.transfer_document_snapshot(),
            self.receipt.transfer_document_snapshot(),
        )
        outgoing = replace(
            issue,
            lines=(
                replace(
                    issue.lines[0],
                    quantity=QuantityVO(Decimal(1)),
                    base_uom=UomCodeVO("PCS"),
                    dimensions=replace(issue.lines[0].dimensions, serial_id=serial),
                ),
            ),
        )
        incoming = replace(
            receipt,
            lines=(
                replace(
                    receipt.lines[0],
                    quantity=QuantityVO(Decimal(1)),
                    base_uom=UomCodeVO("PCS"),
                    dimensions=replace(receipt.lines[0].dimensions, serial_id=serial),
                ),
            ),
        )
        arguments = dict(
            transfer=plan,
            issue_document=a,
            receipt_document=t,
            issue=outgoing,
            receipt=incoming,
        )
        self.assertEqual(self.build(**arguments).lines[0].quantity.value, Decimal(1))
        with self.assertRaises(UnbalancedStockTransferDispatchError):
            self.build(
                **(
                    arguments
                    | dict(
                        receipt=replace(
                            incoming,
                            lines=(
                                replace(
                                    incoming.lines[0],
                                    dimensions=replace(
                                        incoming.lines[0].dimensions,
                                        serial_id=StockSerialIdVO(uuid4()),
                                    ),
                                ),
                            ),
                        )
                    )
                )
            )
        with self.assertRaises(InvalidStockExecutionTransferDocumentSnapshotError):
            replace(
                outgoing,
                lines=(replace(outgoing.lines[0], quantity=QuantityVO(Decimal(2))),),
            ).ensure_valid()
        with self.assertRaises(InvalidStockExecutionTransferDocumentSnapshotError):
            replace(
                outgoing,
                lines=(
                    outgoing.lines[0],
                    replace(
                        outgoing.lines[0],
                        execution_line_id=StockExecutionLineIdVO(uuid4()),
                    ),
                ),
            ).ensure_valid()

    def test_times_cover_both_documents_current_transfer_and_equal_pair_fact_time(
        self,
    ) -> None:
        """Факт не раньше своих документов и перемещения; пара имеет один момент исполнения."""
        a, t = (
            self.issue.transfer_document_snapshot(),
            self.receipt.transfer_document_snapshot(),
        )
        early = self.time - timedelta(seconds=1)
        with self.assertRaises(StockExecutionTimeError):
            self.build(
                issue=replace(a, executed_at=early),
                receipt=replace(t, executed_at=early),
            )
        with self.assertRaises(StockTransferTimeError):
            self.build(receipt=replace(t, executed_at=self.time + timedelta(seconds=1)))
        with self.assertRaises(StockTransferTimeError):
            self.build(
                transfer=replace(
                    self.transfer.dispatch_snapshot(),
                    updated_at=self.time + timedelta(seconds=1),
                )
            )

    def test_existing_route_warehouse_and_location_checks_still_apply(self) -> None:
        """Новый путь передаёт прежней политике проверки A/B/T и активной TRANSIT-локации."""
        with self.assertRaises(WarehouseInactiveError):
            self.build(
                destination_warehouse=replace(self.d.f.destination, is_active=False)
            )
        with self.assertRaises(InventoryError):
            self.build(
                locations=(
                    self.d.source_location,
                    replace(
                        self.d.transit_location, location_type=LocationType.STORAGE
                    ),
                )
            )
        snapshot = self.receipt_document.transfer_dispatch_snapshot()
        execution = self.receipt.transfer_document_snapshot()
        wrong_wh = WarehouseIdVO(uuid4())
        with self.assertRaises(StockTransferDispatchMismatchError):
            self.build(
                receipt_document=replace(snapshot, warehouse_id=wrong_wh),
                receipt=replace(execution, warehouse_id=wrong_wh),
            )

    def test_runtime_snapshot_validation_rejects_missing_types_bool_versions_and_duplicates(
        self,
    ) -> None:
        """Аннотации не заменяют runtime-проверки документных связей и физических полей."""
        snapshot = self.issue.transfer_document_snapshot()
        for changes in (
            dict(document_id=uuid4()),
            dict(document_version=True),
            dict(document_version=-1),
            dict(executed_at=self.time.replace(tzinfo=None)),
            dict(operation_type=StockOperationType.INTERNAL_MOVE),
            dict(lines=()),
            dict(lines=list(snapshot.lines)),
            dict(lines=(None,)),
            dict(lines=(snapshot.lines[0], snapshot.lines[0])),
            dict(lines=(replace(snapshot.lines[0], document_line_id=uuid4()),)),
            dict(lines=(replace(snapshot.lines[0], quantity=QuantityVO(Decimal(0))),)),
        ):
            with self.assertRaises(InvalidStockExecutionTransferDocumentSnapshotError):
                self.build(issue=replace(snapshot, **changes))
        for key, value in (
            ("issue", self.issue),
            ("receipt_document", self.receipt_document),
            ("transfer", self.transfer),
        ):
            with self.assertRaises(InventoryError):
                self.build(**{key: value})

    def test_execution_getter_checks_full_root_and_excludes_internal_move(self) -> None:
        """Прямой обход фабрики не позволяет экспортировать испорченный факт или внутреннее перемещение."""
        with self.assertRaises(InventoryError):
            replace(self.issue, document_version=True).transfer_document_snapshot()
        route = InternalMoveExecutionRouteVO(
            self.d.source_dimensions,
            replace(self.d.source_dimensions, location_id=StockLocationIdVO(uuid4())),
        )
        internal = replace(
            self.issue,
            operation_type=StockOperationType.INTERNAL_MOVE,
            lines=(replace(self.issue.lines[0], route=route),),
        )
        with self.assertRaises(InvalidStockExecutionTransferDocumentSnapshotError):
            internal.transfer_document_snapshot()

    def test_repeated_execution_ids_and_cross_side_fact_ids_are_rejected(self) -> None:
        """Разные документные ссылки не легализуют один execution_id или повтор фактического ID на другой стороне."""
        snapshot = self.receipt.transfer_document_snapshot()
        with self.assertRaises(StockTransferDispatchMismatchError):
            self.build(receipt=replace(snapshot, id=self.issue.id))
        with self.assertRaises(StockTransferDispatchMismatchError):
            self.build(
                receipt=replace(
                    snapshot,
                    lines=(
                        replace(
                            snapshot.lines[0], execution_line_id=self.issue.lines[0].id
                        ),
                        snapshot.lines[1],
                    ),
                )
            )

    def test_hostile_decimal_context_does_not_round_grouping_or_remaining(self) -> None:
        """Пересчёт G, суммы фактов и оба уровня лимитов не зависят от внешнего Decimal context."""
        self.issue = self.fact(self.issue_document, ("20000",), uom="G")
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            self.accept()
            self.issue, self.receipt = self.fact(
                self.issue_document, ("30",)
            ), self.fact(self.receipt_document, ("30",))
            self.assertEqual(self.build().lines[0].quantity.value, Decimal(30))

    def test_two_postings_preserve_total_and_existing_register_dispatch_contract(
        self,
    ) -> None:
        """Автоматический результат применяется прежним корнем, а два прежних проведения дают A=30/T=20."""
        dispatch = self.build()
        out_posting = self.d.posting(
            self.issue, self.d.source_position, self.d.source_location
        )
        in_posting = self.d.posting(
            self.receipt, self.d.transit_position, self.d.transit_location
        )
        self.assertEqual(out_posting.posted_at, in_posting.posted_at)
        source = self.d.source_position.apply_posting_entry(
            out_posting.entries[0].snapshot(),
            expected_version=0,
            inventory_item=self.d.f.item.stock_snapshot(),
            location=self.d.source_location,
            warehouse=self.d.f.source,
        )
        transit = self.d.transit_position.apply_posting_entry(
            in_posting.entries[0].snapshot(),
            expected_version=0,
            inventory_item=self.d.f.item.stock_snapshot(),
            location=self.d.transit_location,
            warehouse=self.d.transit_warehouse,
        )
        self.accept()
        self.assertEqual(
            (source.on_hand_qty.value, transit.on_hand_qty.value),
            (Decimal(30), Decimal(20)),
        )
        self.assertEqual(
            source.on_hand_qty.value + transit.on_hand_qty.value, Decimal(50)
        )
        with self.assertRaises(StockTransferVersionConflictError):
            self.transfer.register_dispatch(
                dispatch, expected_version=self.transfer.version, updated_at=self.time
            )

    def test_input_order_does_not_change_automatic_bindings_result(self) -> None:
        """Фактические ID упорядочиваются как в прежнем ручном результате."""
        snapshot = self.receipt.transfer_document_snapshot()
        self.assertEqual(
            self.build(),
            self.build(
                receipt=replace(snapshot, lines=tuple(reversed(snapshot.lines)))
            ),
        )


if __name__ == "__main__":
    unittest.main()
