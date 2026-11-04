"""Приёмка из транзита: прогресс плана, полная принятая история и остаток по LOT/SERIAL."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from unittest.mock import patch
from uuid import uuid4

from test import test_inventory_stock_transfer_dispatch_domain as dispatch_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.policy.stock_transfer_receipt import (
    StockTransferReceiptPolicy,
)
from src.modules.inventory.domain.policy.stock_transfer_transit_balance import (
    StockTransferTransitBalancePolicy,
)
from src.modules.inventory.domain.stock_execution.transfer_snapshot import (
    StockExecutionTransferSnapshot,
)
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionTransferSnapshotError,
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
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.error import (
    StockLocationInactiveError,
    StockLocationWarehouseMismatchError,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
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
from src.modules.inventory.domain.stock_transfer.aggregate import StockTransfer
from src.modules.inventory.domain.stock_transfer.receipt_plan_snapshot import (
    StockTransferReceiptPlanSnapshot,
)
from src.modules.inventory.domain.stock_transfer.receipt_snapshot import (
    StockTransferReceiptSnapshot,
)
from src.modules.inventory.domain.stock_transfer.dispatch_snapshot import (
    StockTransferDispatchSnapshot,
)
from src.modules.inventory.domain.stock_transfer.transit_balance_snapshot import (
    StockTransferTransitBalanceSnapshot,
)
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferValueError,
    InvalidStockTransferLineError,
    InvalidStockTransferReceiptPlanSnapshotError,
    InvalidStockTransferReceiptSnapshotError,
    InvalidStockTransferTransitBalanceError,
    StockTransferReceiptQuantityExceededError,
    StockTransferReceiptMismatchError,
    StockTransferTransitStockExceededError,
    StockTransferStatusError,
    StockTransferTimeError,
    StockTransferVersionConflictError,
    UnbalancedStockTransferReceiptError,
)
from src.modules.inventory.domain.stock_transfer.value_object.identifier import (
    StockTransferIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.line_id import (
    StockTransferLineIdVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.execution_binding import (
    StockTransferExecutionBindingVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.status import (
    StockTransferStatus,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import WarehouseInactiveError
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class StockTransferReceiptDomainTests(unittest.TestCase):
    """Проверяет согласование T → B без хранения чужих корней или истории внутри StockTransfer."""

    def setUp(self) -> None:
        """Готовит принятые 20 KG в транзите из плана 50 и новую приёмку 10 как 4+6 на B."""
        self.d = dispatch_fixture.StockTransferDispatchDomainTests()
        self.d.setUp()
        self.time = self.d.time
        self.dispatch = self.d.build()
        self.transfer = self.d.register(self.dispatch)
        self.destination_location = StockLocationSnapshot(
            StockLocationIdVO(uuid4()),
            self.d.f.destination.id,
            LocationType.STORAGE,
            True,
        )
        self.destination_dimensions = replace(
            self.d.transit_dimensions, location_id=self.destination_location.id
        )
        self.issue = self.fact(StockOperationType.ISSUE, ("10",))
        self.receipt = self.fact(StockOperationType.RECEIPT, ("4", "6"))
        self.dispatches = (self.dispatch,)
        self.receipts = ()
        self.executions = (self.d.receipt.transfer_snapshot(),)

    def fact(
        self,
        operation: StockOperationType,
        amounts: tuple[str, ...],
        *,
        uom: str = "KG",
    ) -> StockExecution:
        """Создаёт полный факт расхода T или прихода B с сохранёнными вводом и маршрутом."""
        issue = operation is StockOperationType.ISSUE
        dimensions = self.d.transit_dimensions if issue else self.destination_dimensions
        route = (
            IssueExecutionRouteVO(dimensions)
            if issue
            else ReceiptExecutionRouteVO(dimensions)
        )
        return StockExecution.restore(
            identifier=StockExecutionIdVO(uuid4()),
            document_id=StockDocumentIdVO(uuid4()),
            document_version=0,
            operation_type=operation,
            warehouse_id=(
                self.d.transit_warehouse.id if issue else self.d.f.destination.id
            ),
            owner_id=self.d.f.owner,
            executed_at=self.time,
            lines=tuple(
                StockExecutionLine.create(
                    identifier=StockExecutionLineIdVO(uuid4()),
                    document_line_id=StockDocumentLineIdVO(uuid4()),
                    inventory_item=self.d.f.item.execution_snapshot(),
                    quantity=QuantityVO(Decimal(amount)),
                    uom=UomCodeVO(uom),
                    route=route,
                )
                for amount in amounts
            ),
        )

    def balance(self, **changes: object) -> StockTransferTransitBalanceSnapshot:
        """Передаёт всю принятую историю и ровно её транзитные факты."""
        return StockTransferTransitBalancePolicy.build_balance(
            **(
                dict(
                    transfer=self.transfer.receipt_snapshot(),
                    dispatches=self.dispatches,
                    receipts=self.receipts,
                    executions=self.executions,
                )
                | changes
            )
        )

    def bindings(
        self, execution: StockExecution | StockExecutionTransferSnapshot
    ) -> tuple[StockTransferExecutionBindingVO, ...]:
        """Назначает все целые фактические строки одной строке обязательства."""
        return tuple(
            StockTransferExecutionBindingVO(line.id, self.d.f.line.id)
            for line in execution.lines
        )

    def build(self, **changes: object) -> StockTransferReceiptSnapshot:
        """Согласует новую пару со свежим составом транзита."""
        return StockTransferReceiptPolicy.build_receipt(
            **(
                dict(
                    transfer=self.transfer.receipt_snapshot(),
                    balance=self.balance(),
                    issue=self.issue.transfer_snapshot(),
                    receipt=self.receipt.transfer_snapshot(),
                    transit_warehouse=self.d.transit_warehouse,
                    destination_warehouse=self.d.f.destination,
                    locations=(self.d.transit_location, self.destination_location),
                    issue_bindings=self.bindings(self.issue),
                    receipt_bindings=self.bindings(self.receipt),
                )
                | changes
            )
        )

    def register(
        self,
        result: StockTransferReceiptSnapshot | None = None,
        transfer: StockTransfer | None = None,
        **changes: object,
    ) -> StockTransfer:
        """Применяет одну регистрацию одной новой версией."""
        current = self.transfer if transfer is None else transfer
        return current.register_receipt(
            self.build() if result is None else result,
            **(
                dict(
                    expected_version=current.version,
                    updated_at=self.time,
                )
                | changes
            ),
        )

    def accept(self) -> StockTransferReceiptSnapshot:
        """Сохраняет в тестовой истории принятую приёмку и её транзитный расход."""
        result = self.build()
        self.transfer = self.register(result)
        self.receipts += (result,)
        self.executions += (self.issue.transfer_snapshot(),)
        return result

    def test_partial_receipt_updates_only_received_counter_and_one_version(
        self,
    ) -> None:
        """Частичная приёмка не изменяет исходный экземпляр, план, отправку и маршрут."""
        result = self.build()
        partial = self.register(result)
        self.assertEqual(
            (partial.version, partial.status), (4, StockTransferStatus.IN_PROGRESS)
        )
        line = partial.lines[0]
        self.assertEqual(
            (
                line.planned_qty.value,
                line.dispatched_qty.value,
                line.received_qty.value,
                line.in_transit_qty().value,
            ),
            (Decimal(50), Decimal(20), Decimal(10), Decimal(10)),
        )
        self.assertEqual(partial.transit, self.transfer.transit)
        self.assertEqual(self.transfer.lines[0].received_qty.value, Decimal(0))
        self.assertEqual(
            (
                len(result.lines[0].issue_execution_line_ids),
                len(result.lines[0].receipt_execution_line_ids),
            ),
            (1, 2),
        )
        with self.assertRaises(FrozenInstanceError):
            partial.version = 8

    def test_receiving_all_dispatched_goods_does_not_complete_undispatched_plan(
        self,
    ) -> None:
        """Нулевой транзит при плане 50/отправке 20 не завершает перемещение."""
        self.issue = self.fact(StockOperationType.ISSUE, ("20",))
        self.receipt = self.fact(StockOperationType.RECEIPT, ("20",))
        self.accept()
        self.assertEqual(self.transfer.status, StockTransferStatus.IN_PROGRESS)
        self.assertEqual(self.transfer.lines[0].in_transit_qty().value, Decimal(0))
        self.assertEqual(self.balance().lines, ())
        self.assertEqual(
            self.transfer.lines[0].remaining_to_dispatch_qty().value, Decimal(30)
        )

    def test_interleaved_dispatch_and_receipt_finish_only_the_full_plan(self) -> None:
        """20 в транзит, 10 на B, ещё 30 в транзит и 40 на B дают COMPLETED версии 6."""
        self.accept()
        out = self.d.fact(StockOperationType.ISSUE, ("30",))
        inc = self.d.fact(StockOperationType.RECEIPT, ("30",))
        dispatch = self.d.build(
            transfer=self.transfer.dispatch_snapshot(),
            issue=out.transfer_snapshot(),
            receipt=inc.transfer_snapshot(),
            issue_bindings=self.d.bindings(out),
            receipt_bindings=self.d.bindings(inc),
        )
        self.transfer = self.d.register(dispatch, self.transfer)
        self.dispatches += (dispatch,)
        self.executions += (inc.transfer_snapshot(),)
        self.assertEqual(self.transfer.lines[0].received_qty.value, Decimal(10))
        self.assertEqual(self.balance().lines[0].quantity.value, Decimal(40))
        self.issue = self.fact(StockOperationType.ISSUE, ("40",))
        self.receipt = self.fact(StockOperationType.RECEIPT, ("40",))
        result = self.accept()
        self.assertEqual(
            (self.transfer.version, self.transfer.status),
            (6, StockTransferStatus.COMPLETED),
        )
        self.assertEqual(self.transfer.lines[0].received_qty.value, Decimal(50))
        self.assertEqual(self.balance().lines, ())
        self.assertEqual(self.d.restore(self.transfer), self.transfer)
        self.transfer.dispatch_snapshot().ensure_valid()
        for action in (
            lambda: self.register(result),
            lambda: self.d.build(transfer=self.transfer.dispatch_snapshot()),
        ):
            with self.assertRaises(StockTransferStatusError):
                action()

    def test_single_full_receipt_completes_a_fully_dispatched_plan(self) -> None:
        """Одна приёмка 50 допустима сразу после одной полной отправки 50."""
        out = self.d.fact(StockOperationType.ISSUE, ("50",))
        inc = self.d.fact(StockOperationType.RECEIPT, ("50",))
        dispatch = self.d.build(
            issue=out.transfer_snapshot(),
            receipt=inc.transfer_snapshot(),
            issue_bindings=self.d.bindings(out),
            receipt_bindings=self.d.bindings(inc),
        )
        self.transfer = self.d.register(dispatch)
        self.dispatches = (dispatch,)
        self.executions = (inc.transfer_snapshot(),)
        self.issue = self.fact(StockOperationType.ISSUE, ("50",))
        self.receipt = self.fact(StockOperationType.RECEIPT, ("50",))
        self.assertEqual(self.register().status, StockTransferStatus.COMPLETED)

    def test_balance_deducts_previous_receipts_and_rejects_repeated_fact_ids(
        self,
    ) -> None:
        """Уже принятые количества вычитаются; пересобрать прежний расход по новой версии нельзя."""
        self.accept()
        balance = self.balance()
        self.assertEqual(balance.lines[0].quantity.value, Decimal(10))
        self.assertEqual(len(balance.execution_ids), 4)
        with self.assertRaises(StockTransferReceiptMismatchError):
            self.build()
        self.issue = self.fact(StockOperationType.ISSUE, ("11",))
        self.receipt = self.fact(StockOperationType.RECEIPT, ("11",))
        with self.assertRaises(StockTransferTransitStockExceededError):
            self.build()

    def test_lot_composition_not_just_total_limits_receipt(self) -> None:
        """В транзите LOT A=8/B=12: нельзя принять 10 A, даже если общий остаток 20."""
        a, b = StockLotIdVO(uuid4()), StockLotIdVO(uuid4())
        fact = self.executions[0]
        self.executions = (
            replace(
                fact,
                lines=tuple(
                    replace(line, dimensions=replace(line.dimensions, lot_id=lot))
                    for line, lot in zip(fact.lines, (a, b))
                ),
            ),
        )
        balance = self.balance()
        self.assertEqual(
            sorted(row.quantity.value for row in balance.lines),
            [Decimal(8), Decimal(12)],
        )
        issue = self.issue.transfer_snapshot()
        receipt = self.receipt.transfer_snapshot()
        for lot, valid in ((a, False), (b, True), (StockLotIdVO(uuid4()), False)):
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
            with self.subTest(lot=lot):
                if valid:
                    self.assertEqual(
                        self.build(issue=outgoing, receipt=incoming)
                        .lines[0]
                        .quantity.value,
                        Decimal(10),
                    )
                else:
                    with self.assertRaises(StockTransferTransitStockExceededError):
                        self.build(issue=outgoing, receipt=incoming)

    def test_pair_cannot_change_lot_serial_status_or_quantity(self) -> None:
        """Даже одинаковая сумма сторон не разрешает подмену сохраняемых измерений."""
        fact = self.receipt.transfer_snapshot()
        for field, value in (
            ("lot_id", StockLotIdVO(uuid4())),
            ("stock_status", StockStatus.DAMAGED),
        ):
            changed = replace(
                fact,
                lines=tuple(
                    replace(line, dimensions=replace(line.dimensions, **{field: value}))
                    for line in fact.lines
                ),
            )
            with self.assertRaises(UnbalancedStockTransferReceiptError):
                self.build(receipt=changed)
        with self.assertRaises(UnbalancedStockTransferReceiptError):
            self.build(
                receipt=replace(
                    fact,
                    lines=(
                        replace(fact.lines[0], quantity=QuantityVO(Decimal(5))),
                        fact.lines[1],
                    ),
                )
            )
        issue = self.issue.transfer_snapshot()
        with self.assertRaises(StockTransferTransitStockExceededError):
            self.build(
                issue=replace(
                    issue,
                    lines=tuple(
                        replace(
                            line,
                            dimensions=replace(
                                line.dimensions, stock_status=StockStatus.DAMAGED
                            ),
                        )
                        for line in issue.lines
                    ),
                ),
                receipt=replace(
                    fact,
                    lines=tuple(
                        replace(
                            line,
                            dimensions=replace(
                                line.dimensions, stock_status=StockStatus.DAMAGED
                            ),
                        )
                        for line in fact.lines
                    ),
                ),
            )

    def serial_context(
        self,
    ) -> tuple[
        StockTransferReceiptPlanSnapshot,
        StockTransferDispatchSnapshot,
        StockExecutionTransferSnapshot,
        StockTransferTransitBalanceSnapshot,
        StockExecutionTransferSnapshot,
        StockExecutionTransferSnapshot,
        tuple[StockSerialIdVO, StockSerialIdVO],
    ]:
        """Готовит принятые S1 и S2 в PCS и новую приёмку S1 без актуальных внешних корней."""
        serials = (StockSerialIdVO(uuid4()), StockSerialIdVO(uuid4()))
        plan = self.transfer.receipt_snapshot()
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
        history = self.executions[0]
        history = replace(
            history,
            lines=tuple(
                replace(
                    line,
                    base_uom=UomCodeVO("PCS"),
                    quantity=QuantityVO(Decimal(1)),
                    dimensions=replace(line.dimensions, serial_id=serial),
                )
                for line, serial in zip(history.lines, serials)
            ),
        )
        dispatch = replace(
            self.dispatch,
            lines=(
                replace(
                    self.dispatch.lines[0],
                    base_uom=UomCodeVO("PCS"),
                    quantity=QuantityVO(Decimal(2)),
                ),
            ),
        )
        issue = self.issue.transfer_snapshot()
        issue = replace(
            issue,
            lines=(
                replace(
                    issue.lines[0],
                    base_uom=UomCodeVO("PCS"),
                    quantity=QuantityVO(Decimal(1)),
                    dimensions=replace(issue.lines[0].dimensions, serial_id=serials[0]),
                ),
            ),
        )
        receipt = self.receipt.transfer_snapshot()
        receipt = replace(
            receipt,
            lines=(
                replace(
                    receipt.lines[0],
                    base_uom=UomCodeVO("PCS"),
                    quantity=QuantityVO(Decimal(1)),
                    dimensions=replace(
                        receipt.lines[0].dimensions, serial_id=serials[0]
                    ),
                ),
            ),
        )
        balance = self.balance(
            transfer=plan, dispatches=(dispatch,), executions=(history,)
        )
        return plan, dispatch, history, balance, issue, receipt, serials

    def test_serial_can_be_received_once_and_other_serials_do_not_cover_it(
        self,
    ) -> None:
        """После приёмки S1 остаток S2 не даёт повторно принять S1 с новыми фактическими ID."""
        plan, dispatch, history, balance, issue, receipt, serials = (
            self.serial_context()
        )
        result = self.build(
            transfer=plan,
            balance=balance,
            issue=issue,
            receipt=receipt,
            receipt_bindings=self.bindings(receipt),
        )
        plan = replace(
            plan,
            version=4,
            lines=(replace(plan.lines[0], received_qty=QuantityVO(Decimal(1))),),
        )
        after = self.balance(
            transfer=plan,
            dispatches=(dispatch,),
            receipts=(result,),
            executions=(history, issue),
        )
        self.assertEqual(after.lines[0].dimensions.serial_id, serials[1])
        new_issue = replace(
            issue,
            id=StockExecutionIdVO(uuid4()),
            lines=(replace(issue.lines[0], id=StockExecutionLineIdVO(uuid4())),),
        )
        new_receipt = replace(
            receipt,
            id=StockExecutionIdVO(uuid4()),
            lines=(replace(receipt.lines[0], id=StockExecutionLineIdVO(uuid4())),),
        )
        with self.assertRaises(StockTransferTransitStockExceededError):
            self.build(
                transfer=plan,
                balance=after,
                issue=new_issue,
                receipt=new_receipt,
                issue_bindings=self.bindings(new_issue),
                receipt_bindings=self.bindings(new_receipt),
            )
        with self.assertRaises(UnbalancedStockTransferReceiptError):
            self.build(
                transfer=replace(
                    plan,
                    version=3,
                    lines=(
                        replace(plan.lines[0], received_qty=QuantityVO(Decimal(0))),
                    ),
                ),
                balance=balance,
                issue=issue,
                receipt=replace(
                    receipt,
                    lines=(
                        replace(
                            receipt.lines[0],
                            dimensions=replace(
                                receipt.lines[0].dimensions, serial_id=serials[1]
                            ),
                        ),
                    ),
                ),
                receipt_bindings=self.bindings(receipt),
            )

    def test_serial_facts_require_one_pcs_and_unique_instances(self) -> None:
        """Нельзя заменить один серийный экземпляр количеством 2 или двумя строками одной серии."""
        plan, _, _, balance, issue, receipt, _ = self.serial_context()
        for lines in (
            (replace(issue.lines[0], quantity=QuantityVO(Decimal(2))),),
            (
                issue.lines[0],
                replace(issue.lines[0], id=StockExecutionLineIdVO(uuid4())),
            ),
        ):
            with self.assertRaises(InvalidStockExecutionTransferSnapshotError):
                self.build(
                    transfer=plan,
                    balance=balance,
                    issue=replace(issue, lines=lines),
                    receipt=receipt,
                )

    def test_duplicate_serial_dispatch_across_history_is_rejected(self) -> None:
        """Разные исполнения не позволяют добавить в транзит один экземпляр повторно."""
        plan, dispatch, history, _, _, _, _ = self.serial_context()
        second_history = replace(
            history,
            id=StockExecutionIdVO(uuid4()),
            lines=(replace(history.lines[0], id=StockExecutionLineIdVO(uuid4())),),
        )
        second = replace(
            dispatch,
            transfer_version=3,
            issue_execution_id=StockExecutionIdVO(uuid4()),
            receipt_execution_id=second_history.id,
            lines=(
                replace(
                    dispatch.lines[0],
                    quantity=QuantityVO(Decimal(1)),
                    issue_execution_line_ids=(StockExecutionLineIdVO(uuid4()),),
                    receipt_execution_line_ids=(second_history.lines[0].id,),
                ),
            ),
        )
        plan = replace(
            plan,
            version=4,
            lines=(replace(plan.lines[0], dispatched_qty=QuantityVO(Decimal(3))),),
        )
        with self.assertRaises(InvalidStockTransferTransitBalanceError):
            self.balance(
                transfer=plan,
                dispatches=(dispatch, second),
                executions=(history, second_history),
            )

    def test_history_must_be_complete_unique_and_match_progress(self) -> None:
        """Пропуск перехода, повтор или неверные суммы истории не создают пригодный снимок."""
        result = self.accept()
        defaults = dict(
            transfer=self.transfer.receipt_snapshot(),
            dispatches=self.dispatches,
            receipts=self.receipts,
            executions=self.executions,
        )
        for changes in (
            dict(dispatches=()),
            dict(receipts=()),
            dict(executions=self.executions[:1]),
            dict(dispatches=self.dispatches * 2),
            dict(receipts=(result, result)),
            dict(executions=self.executions * 2),
            dict(receipts=(replace(result, transfer_version=5),)),
            dict(transfer=replace(defaults["transfer"], version=5)),
            dict(
                transfer=replace(
                    defaults["transfer"],
                    lines=(
                        replace(
                            defaults["transfer"].lines[0],
                            received_qty=QuantityVO(Decimal(9)),
                        ),
                    ),
                )
            ),
            dict(dispatches=list(self.dispatches)),
            dict(executions=(None,)),
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(InventoryError):
                    StockTransferTransitBalancePolicy.build_balance(
                        **(defaults | changes)
                    )
        # Входной порядок не является порядком регистрации: версии задают его явно.
        self.assertEqual(
            self.balance(executions=tuple(reversed(self.executions))), self.balance()
        )

    def test_history_requires_matching_route_owner_facts_scope_and_time(self) -> None:
        """Чужой результат, факт или адрес не подтверждает приход в транзит этого перемещения."""
        fact = self.executions[0]
        for changes in (
            dict(transfer_id=StockTransferIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(destination_warehouse_id=WarehouseIdVO(uuid4())),
            dict(executed_at=self.time + timedelta(seconds=1)),
            dict(
                lines=(
                    replace(self.dispatch.lines[0], quantity=QuantityVO(Decimal(19))),
                )
            ),
        ):
            with self.assertRaises(InventoryError):
                self.balance(dispatches=(replace(self.dispatch, **changes),))
        for changes in (
            dict(id=StockExecutionIdVO(uuid4())),
            dict(operation_type=StockOperationType.ISSUE),
            dict(warehouse_id=WarehouseIdVO(uuid4())),
            dict(executed_at=self.time - timedelta(seconds=1)),
            dict(
                lines=(
                    replace(
                        fact.lines[0],
                        dimensions=replace(
                            fact.lines[0].dimensions,
                            location_id=StockLocationIdVO(uuid4()),
                        ),
                    ),
                    fact.lines[1],
                )
            ),
            dict(
                lines=(
                    replace(
                        fact.lines[0],
                        inventory_item_id=self.d.f.new_line().inventory_item_id,
                        base_uom=UomCodeVO("G"),
                    ),
                    fact.lines[1],
                )
            ),
        ):
            with self.assertRaises(InventoryError):
                self.balance(executions=(replace(fact, **changes),))
        extra = replace(fact, id=StockExecutionIdVO(uuid4()))
        with self.assertRaises(InvalidStockTransferTransitBalanceError):
            self.balance(executions=(fact, extra))

    def test_history_cannot_receive_goods_before_their_dispatch(self) -> None:
        """Нельзя покрыть неверный ранний расход более поздней отправкой той же партии."""
        result = self.accept()
        history_issue = self.executions[1]
        bad_lot = StockLotIdVO(uuid4())
        history_issue = replace(
            history_issue,
            lines=tuple(
                replace(line, dimensions=replace(line.dimensions, lot_id=bad_lot))
                for line in history_issue.lines
            ),
        )
        with self.assertRaises(InvalidStockTransferTransitBalanceError):
            self.balance(
                receipts=(result,), executions=(self.executions[0], history_issue)
            )

    def test_repeated_history_execution_and_line_ids_are_rejected(self) -> None:
        """Разные версии не легализуют повтор исторических ID обеих сторон пары."""
        result = self.accept()
        for changed in (
            replace(result, receipt_execution_id=self.dispatch.issue_execution_id),
            replace(
                result,
                lines=(
                    replace(
                        result.lines[0],
                        receipt_execution_line_ids=self.dispatch.lines[
                            0
                        ].issue_execution_line_ids,
                    ),
                ),
            ),
        ):
            with self.assertRaises(InvalidStockTransferTransitBalanceError):
                self.balance(receipts=(changed,))

    def test_balance_cannot_be_used_for_another_version_or_scope(self) -> None:
        """Подготовленный остаток устаревает после любого зарегистрированного движения."""
        old = self.balance()
        self.accept()
        with self.assertRaises(StockTransferVersionConflictError):
            self.build(balance=old)
        current = self.balance()
        for changes in (
            dict(transfer_id=StockTransferIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(lines=()),
        ):
            with self.assertRaises(InvalidStockTransferTransitBalanceError):
                self.build(balance=replace(current, **changes))

    def test_balance_rows_and_history_ids_are_validated_at_consumption(self) -> None:
        """Прямая сборка dataclass не обходит проверку типов, нулей, повторов и сумм снимка."""
        balance = self.balance()
        row = balance.lines[0]
        for changes in (
            dict(transfer_version=True),
            dict(lines=[row]),
            dict(lines=(row, row)),
            dict(lines=(None,)),
            dict(execution_ids=()),
            dict(execution_line_ids=balance.execution_line_ids * 2),
            dict(lines=(replace(row, quantity=QuantityVO(Decimal(0))),)),
            dict(
                lines=(
                    replace(
                        row,
                        dimensions=replace(
                            row.dimensions, location_id=self.destination_location.id
                        ),
                    ),
                )
            ),
            dict(lines=(replace(row, quantity=QuantityVO(Decimal(19))),)),
            dict(
                lines=(replace(row, transfer_line_id=StockTransferLineIdVO(uuid4())),)
            ),
        ):
            with self.assertRaises(InvalidStockTransferTransitBalanceError):
                self.build(balance=replace(balance, **changes))

    def test_pair_requires_current_active_transit_and_destination_only(self) -> None:
        """Приёмка зависит от T/B и их адресов; деактивация исходного A уже не препятствует ей."""
        self.d.f.source = replace(self.d.f.source, is_active=False)
        self.assertEqual(self.build().lines[0].quantity.value, Decimal(10))
        for key, warehouse in (
            ("transit_warehouse", self.d.transit_warehouse),
            ("destination_warehouse", self.d.f.destination),
        ):
            with self.assertRaises(WarehouseInactiveError):
                self.build(**{key: replace(warehouse, is_active=False)})
        with self.assertRaises(StockLocationInactiveError):
            self.build(
                locations=(
                    self.d.transit_location,
                    replace(self.destination_location, is_active=False),
                )
            )
        with self.assertRaises(StockLocationWarehouseMismatchError):
            self.build(
                locations=(
                    self.d.transit_location,
                    replace(self.destination_location, warehouse_id=self.d.f.source.id),
                )
            )

    def test_pair_requires_exact_locations_and_fixed_transit_address(self) -> None:
        """Адреса охватывают ровно фактические строки, расход только из выбранного TRANSIT."""
        for locations in (
            (self.destination_location,),
            (
                self.d.transit_location,
                self.destination_location,
                self.d.source_location,
            ),
            (
                self.d.transit_location,
                self.destination_location,
                self.destination_location,
            ),
            (
                replace(self.d.transit_location, location_type=LocationType.STORAGE),
                self.destination_location,
            ),
        ):
            with self.assertRaises(InventoryError):
                self.build(locations=locations)
        issue = self.issue.transfer_snapshot()
        with self.assertRaises(InventoryError):
            self.build(
                issue=replace(
                    issue,
                    lines=(
                        replace(
                            issue.lines[0],
                            dimensions=replace(
                                issue.lines[0].dimensions,
                                location_id=StockLocationIdVO(uuid4()),
                            ),
                        ),
                    ),
                )
            )

    def test_shared_grouping_validates_snapshots_when_called_directly(self) -> None:
        """Прямой вызов общей политики также отвергает невалидные факты и состав плана."""
        from src.modules.inventory.domain.policy.stock_transfer_execution_grouping import (
            StockTransferExecutionGroupingPolicy,
        )

        plan = {row.id: row for row in self.transfer.receipt_snapshot().lines}
        for execution, rows in (
            (None, plan),
            (self.issue.transfer_snapshot(), {self.d.f.line.id: None}),
            (
                self.issue.transfer_snapshot(),
                {StockTransferLineIdVO(uuid4()): next(iter(plan.values()))},
            ),
        ):
            with self.assertRaises(InventoryError):
                StockTransferExecutionGroupingPolicy.group(
                    execution,
                    self.bindings(self.issue),
                    rows,
                    StockTransferReceiptMismatchError,
                )

    def test_pair_assignments_cover_every_whole_fact_once(self) -> None:
        """Назначения не пропускают и не повторяют факты; одинаковый товар не заменяет ID строки плана."""
        assigned = self.bindings(self.receipt)
        for bindings in (
            assigned[:1],
            assigned * 2,
            (
                replace(assigned[0], transfer_line_id=StockTransferLineIdVO(uuid4())),
                assigned[1],
            ),
            (
                replace(assigned[0], execution_line_id=StockExecutionLineIdVO(uuid4())),
                assigned[1],
            ),
        ):
            with self.assertRaises(StockTransferReceiptMismatchError):
                self.build(receipt_bindings=bindings)

    def test_pair_can_split_receipt_between_destination_addresses(self) -> None:
        """Целый расход 10 допускает приход 4+6 по двум активным адресам B."""
        second = replace(self.destination_location, id=StockLocationIdVO(uuid4()))
        receipt = self.receipt.transfer_snapshot()
        receipt = replace(
            receipt,
            lines=(
                receipt.lines[0],
                replace(
                    receipt.lines[1],
                    dimensions=replace(
                        receipt.lines[1].dimensions, location_id=second.id
                    ),
                ),
            ),
        )
        self.assertEqual(
            self.build(
                receipt=receipt,
                locations=(self.d.transit_location, self.destination_location, second),
            )
            .lines[0]
            .quantity.value,
            Decimal(10),
        )

    def test_receipt_pair_rejects_wrong_execution_scope_identity_and_time(self) -> None:
        """Чужие склад/владелец, одинаковые ID сторон и разное время не образуют приёмку."""
        issue, receipt = (
            self.issue.transfer_snapshot(),
            self.receipt.transfer_snapshot(),
        )
        for changes in (
            dict(warehouse_id=self.d.f.source.id),
            dict(operation_type=StockOperationType.RECEIPT),
            dict(id=receipt.id),
            dict(executed_at=self.time - timedelta(seconds=1)),
        ):
            with self.assertRaises(InventoryError):
                self.build(issue=replace(issue, **changes))
        with self.assertRaises(InventoryError):
            self.build(
                receipt=replace(
                    receipt,
                    lines=tuple(
                        replace(
                            line,
                            dimensions=replace(
                                line.dimensions, owner_id=StockOwnerIdVO(uuid4())
                            ),
                        )
                        for line in receipt.lines
                    ),
                )
            )

    def test_registration_rechecks_versions_before_arithmetic_and_rejects_replay(
        self,
    ) -> None:
        """Старая регистрация и ожидаемая версия отклоняются до собственной арифметики."""
        result = self.build()
        partial = self.register(result)
        with self.assertRaises(StockTransferVersionConflictError):
            self.register(result, partial)
        with patch(
            "src.modules.inventory.domain.stock_transfer.aggregate.QuantityArithmeticPolicy.add",
            side_effect=RuntimeError("must not run"),
        ):
            with self.assertRaises(StockTransferVersionConflictError):
                self.register(result, expected_version=2)
        for version in (True, -1, Decimal(3)):
            with self.assertRaises(InvalidStockTransferValueError):
                self.register(result, expected_version=version)
        with self.assertRaises(StockTransferVersionConflictError):
            self.register(replace(result, transfer_version=2))

    def test_registration_checks_scope_lines_units_and_receipt_limit(self) -> None:
        """Корень повторно сверяет весь собственный контракт, даже у вручную собранного результата."""
        result = self.build()
        for changes in (
            dict(transfer_id=StockTransferIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
            dict(destination_warehouse_id=WarehouseIdVO(uuid4())),
            dict(
                lines=(
                    replace(
                        result.lines[0], transfer_line_id=StockTransferLineIdVO(uuid4())
                    ),
                )
            ),
            dict(lines=(replace(result.lines[0], base_uom=UomCodeVO("G")),)),
        ):
            with self.assertRaises(StockTransferReceiptMismatchError):
                self.register(replace(result, **changes))
        with self.assertRaises(StockTransferReceiptQuantityExceededError):
            self.register(
                replace(
                    result,
                    lines=(replace(result.lines[0], quantity=QuantityVO(Decimal(21))),),
                )
            )

    def test_receipt_time_is_explicit_monotonic_and_normalized_to_utc(self) -> None:
        """Равное время допустимо, наивное/раннее запрещено, aware-ввод нормализуется."""
        result = self.build()
        for time in (
            self.time.replace(tzinfo=None),
            self.time - timedelta(seconds=1),
            None,
        ):
            with self.assertRaises(StockTransferTimeError):
                self.register(result, updated_at=time)
        with self.assertRaises(StockTransferTimeError):
            self.register(replace(result, executed_at=self.time + timedelta(seconds=1)))
        issue = replace(
            self.issue.transfer_snapshot(), executed_at=self.time - timedelta(seconds=1)
        )
        receipt = replace(
            self.receipt.transfer_snapshot(), executed_at=issue.executed_at
        )
        with self.assertRaises(StockTransferTimeError):
            self.build(issue=issue, receipt=receipt)
        self.assertEqual(
            self.register(
                result, updated_at=self.time.astimezone(timezone(timedelta(hours=3)))
            ).updated_at.utcoffset(),
            timedelta(0),
        )

    def test_result_and_plan_runtime_types_are_not_only_annotations(self) -> None:
        """Сырые UUID, bool-версия, пустые и повторные строки/ID отвергаются получателем снимка."""
        result = self.build()
        for changes in (
            dict(transfer_version=True),
            dict(executed_at=self.time.replace(tzinfo=None)),
            dict(lines=()),
            dict(lines=(result.lines[0], result.lines[0])),
            dict(issue_execution_id=result.receipt_execution_id),
            dict(lines=(replace(result.lines[0], quantity=QuantityVO(Decimal(0))),)),
            dict(
                lines=(
                    replace(
                        result.lines[0],
                        receipt_execution_line_ids=result.lines[
                            0
                        ].issue_execution_line_ids,
                    ),
                )
            ),
        ):
            with self.assertRaises(InvalidStockTransferReceiptSnapshotError):
                self.register(replace(result, **changes))
        plan = self.transfer.receipt_snapshot()
        for changes in (
            dict(version=True),
            dict(lines=list(plan.lines)),
            dict(lines=(plan.lines[0], plan.lines[0])),
            dict(lines=(replace(plan.lines[0], received_qty=QuantityVO(Decimal(21))),)),
            dict(status=StockTransferStatus.COMPLETED),
        ):
            with self.assertRaises(InvalidStockTransferReceiptPlanSnapshotError):
                self.build(transfer=replace(plan, **changes))

    def test_restore_enforces_full_progress_and_terminal_state_without_context(
        self,
    ) -> None:
        """Историческое восстановление принимает оба счётчика и не требует актуальных складов или фактов."""
        partial = self.register()
        self.assertEqual(self.d.restore(partial), partial)
        for received in (None, Decimal(1)):
            with self.assertRaises(InvalidStockTransferLineError):
                self.d.restore(
                    partial, lines=(replace(partial.lines[0], received_qty=received),)
                )
        with self.assertRaises(StockTransferReceiptQuantityExceededError):
            self.d.restore(
                partial,
                lines=(
                    replace(partial.lines[0], received_qty=QuantityVO(Decimal(21))),
                ),
            )
        for changes in (
            dict(status=StockTransferStatus.COMPLETED),
            dict(status=StockTransferStatus.CONFIRMED),
            dict(transit=None),
        ):
            with self.assertRaises(InvalidStockTransferValueError):
                self.d.restore(partial, **changes)
        complete_line = replace(
            partial.lines[0],
            dispatched_qty=partial.lines[0].planned_qty,
            received_qty=partial.lines[0].planned_qty,
        )
        with self.assertRaises(InvalidStockTransferValueError):
            self.d.restore(partial, lines=(complete_line,))
        completed = self.d.restore(
            partial, lines=(complete_line,), status=StockTransferStatus.COMPLETED
        )
        for action in (
            lambda: completed.cancel(
                expected_version=completed.version, updated_at=self.time
            ),
            lambda: completed.remove_line(
                complete_line.id,
                expected_version=completed.version,
                updated_at=self.time,
            ),
        ):
            with self.assertRaises(StockTransferStatusError):
                action()

    def test_receipt_cannot_use_another_plan_lines_stock_of_the_same_item(self) -> None:
        """Даже баланс обеих сторон по одному товару не разрешает перенос между обязательствами."""
        plan = self.transfer.receipt_snapshot()
        first = replace(plan.lines[0], dispatched_qty=QuantityVO(Decimal(10)))
        second = replace(first, id=StockTransferLineIdVO(uuid4()))
        plan = replace(plan, lines=(first, second))
        dispatch = replace(
            self.dispatch,
            lines=(
                replace(
                    self.dispatch.lines[0],
                    quantity=QuantityVO(Decimal(8)),
                    receipt_execution_line_ids=(self.executions[0].lines[0].id,),
                ),
                replace(
                    self.dispatch.lines[0],
                    transfer_line_id=second.id,
                    quantity=QuantityVO(Decimal(12)),
                    issue_execution_line_ids=(StockExecutionLineIdVO(uuid4()),),
                    receipt_execution_line_ids=(self.executions[0].lines[1].id,),
                ),
            ),
        )
        # У второго обязательства должно быть именно отправлено 12; первый остаток 8.
        plan = replace(
            plan,
            lines=(
                replace(first, dispatched_qty=QuantityVO(Decimal(8))),
                replace(second, dispatched_qty=QuantityVO(Decimal(12))),
            ),
        )
        balance = self.balance(transfer=plan, dispatches=(dispatch,))
        with self.assertRaises(StockTransferTransitStockExceededError):
            self.build(
                transfer=plan, balance=balance
            )  # Оба факта назначены первому обязательству: там лишь 8.
        self.assertEqual(
            self.build(
                transfer=plan,
                balance=balance,
                issue_bindings=tuple(
                    replace(binding, transfer_line_id=second.id)
                    for binding in self.bindings(self.issue)
                ),
                receipt_bindings=tuple(
                    replace(binding, transfer_line_id=second.id)
                    for binding in self.bindings(self.receipt)
                ),
            )
            .lines[0]
            .transfer_line_id,
            second.id,
        )

    def test_lot_balance_deducts_receipt_from_only_its_lot(self) -> None:
        """Принятые 10 B оставляют A=8/B=2, без взаимного покрытия партий."""
        a, b = StockLotIdVO(uuid4()), StockLotIdVO(uuid4())
        history = self.executions[0]
        self.executions = (
            replace(
                history,
                lines=tuple(
                    replace(line, dimensions=replace(line.dimensions, lot_id=lot))
                    for line, lot in zip(history.lines, (a, b))
                ),
            ),
        )
        issue, receipt = (
            self.issue.transfer_snapshot(),
            self.receipt.transfer_snapshot(),
        )
        issue = replace(
            issue,
            lines=tuple(
                replace(line, dimensions=replace(line.dimensions, lot_id=b))
                for line in issue.lines
            ),
        )
        receipt = replace(
            receipt,
            lines=tuple(
                replace(line, dimensions=replace(line.dimensions, lot_id=b))
                for line in receipt.lines
            ),
        )
        registration = self.build(issue=issue, receipt=receipt)
        self.transfer = self.register(registration)
        remaining = self.balance(
            receipts=(registration,), executions=(*self.executions, issue)
        )
        self.assertEqual(
            {row.dimensions.lot_id: row.quantity.value for row in remaining.lines},
            {a: Decimal(8), b: Decimal(2)},
        )

    def test_all_plan_lines_must_be_received_before_completion(self) -> None:
        """Полная приёмка первой строки не завершает план с другой неотправленной строкой."""
        second = self.d.f.new_line()
        full_line = replace(
            self.transfer.lines[0],
            planned_qty=QuantityVO(Decimal(20)),
            conversion=replace(
                self.transfer.lines[0].conversion, quantity=QuantityVO(Decimal(20000))
            ),
        )
        self.transfer = self.d.restore(self.transfer, lines=(full_line, second))
        self.issue = self.fact(StockOperationType.ISSUE, ("20",))
        self.receipt = self.fact(StockOperationType.RECEIPT, ("20",))
        accepted = self.register()
        self.assertEqual(accepted.status, StockTransferStatus.IN_PROGRESS)
        self.assertEqual(accepted.lines[0].received_qty, accepted.lines[0].planned_qty)
        self.assertEqual(accepted.lines[1].received_qty.value, Decimal(0))

    def test_quantity_arithmetic_and_gram_conversion_ignore_hostile_decimal_context(
        self,
    ) -> None:
        """Группировка, вычитание транзита и прогресс точны даже при внешней точности 1."""
        self.issue = self.fact(StockOperationType.ISSUE, ("10000",), uom="G")
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            self.accept()
            self.assertEqual(self.balance().lines[0].quantity.value, Decimal(10))
            self.assertEqual(self.transfer.lines[0].received_qty.value, Decimal(10))

    def test_physical_postings_interleave_and_preserve_total_with_completed_transfer(
        self,
    ) -> None:
        """Существующие проведения дают A/T/B: 30/20/0 → 30/10/10 → 0/40/10 → 0/0/50."""
        a, transit = self.d.source_position, self.d.transit_position
        b = replace(
            transit,
            id=StockPositionIdVO(uuid4()),
            dimensions=self.destination_dimensions,
        )

        def move(
            issue: StockExecution,
            receipt: StockExecution,
            source: StockPosition,
            destination: StockPosition,
            source_location: StockLocationSnapshot,
            destination_location: StockLocationSnapshot,
            source_warehouse: WarehouseSnapshot,
            destination_warehouse: WarehouseSnapshot,
        ) -> tuple[StockPosition, StockPosition]:
            """Строит оба физических кандидата с одним временем, затем применяет существующую защиту позиций."""
            out = self.d.posting(issue, source, source_location)
            inc = self.d.posting(receipt, destination, destination_location)
            self.assertEqual(out.posted_at, inc.posted_at)
            for entry in out.entries:
                source = source.apply_posting_entry(
                    entry.snapshot(),
                    expected_version=source.version,
                    inventory_item=self.d.f.item.stock_snapshot(),
                    location=source_location,
                    warehouse=source_warehouse,
                )
            for entry in inc.entries:
                destination = destination.apply_posting_entry(
                    entry.snapshot(),
                    expected_version=destination.version,
                    inventory_item=self.d.f.item.stock_snapshot(),
                    location=destination_location,
                    warehouse=destination_warehouse,
                )
            return source, destination

        a, transit = move(
            self.d.issue,
            self.d.receipt,
            a,
            transit,
            self.d.source_location,
            self.d.transit_location,
            self.d.f.source,
            self.d.transit_warehouse,
        )
        self.assertEqual(
            (a.on_hand_qty.value, transit.on_hand_qty.value, b.on_hand_qty.value),
            (Decimal(30), Decimal(20), Decimal(0)),
        )
        self.accept()
        transit, b = move(
            self.issue,
            self.receipt,
            transit,
            b,
            self.d.transit_location,
            self.destination_location,
            self.d.transit_warehouse,
            self.d.f.destination,
        )
        self.assertEqual(
            (a.on_hand_qty.value, transit.on_hand_qty.value, b.on_hand_qty.value),
            (Decimal(30), Decimal(10), Decimal(10)),
        )
        out, inc = self.d.fact(StockOperationType.ISSUE, ("30",)), self.d.fact(
            StockOperationType.RECEIPT, ("30",)
        )
        dispatch = self.d.build(
            transfer=self.transfer.dispatch_snapshot(),
            issue=out.transfer_snapshot(),
            receipt=inc.transfer_snapshot(),
            issue_bindings=self.d.bindings(out),
            receipt_bindings=self.d.bindings(inc),
        )
        self.transfer = self.d.register(dispatch, self.transfer)
        self.dispatches += (dispatch,)
        self.executions += (inc.transfer_snapshot(),)
        a, transit = move(
            out,
            inc,
            a,
            transit,
            self.d.source_location,
            self.d.transit_location,
            self.d.f.source,
            self.d.transit_warehouse,
        )
        self.assertEqual(
            (a.on_hand_qty.value, transit.on_hand_qty.value, b.on_hand_qty.value),
            (Decimal(0), Decimal(40), Decimal(10)),
        )
        self.issue, self.receipt = self.fact(
            StockOperationType.ISSUE, ("40",)
        ), self.fact(StockOperationType.RECEIPT, ("40",))
        self.accept()
        transit, b = move(
            self.issue,
            self.receipt,
            transit,
            b,
            self.d.transit_location,
            self.destination_location,
            self.d.transit_warehouse,
            self.d.f.destination,
        )
        self.assertEqual(
            (a.on_hand_qty.value, transit.on_hand_qty.value, b.on_hand_qty.value),
            (Decimal(0), Decimal(0), Decimal(50)),
        )
        self.assertEqual(
            a.on_hand_qty.value + transit.on_hand_qty.value + b.on_hand_qty.value,
            Decimal(50),
        )
        self.assertEqual(self.transfer.status, StockTransferStatus.COMPLETED)
        self.assertEqual(self.balance().lines, ())


if __name__ == "__main__":
    unittest.main()
