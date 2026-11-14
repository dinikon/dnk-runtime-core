"""Согласованная отправка в отдельный транзит: пара ISSUE/RECEIPT, сохраняемые измерения и прогресс StockTransfer."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from unittest.mock import patch
from uuid import uuid4

from test import test_inventory_stock_transfer_domain as transfer_fixture
from src.modules.inventory.domain.availability_pool.aggregate import AvailabilityPool
from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.error import (
    InventoryError,
    NegativeStockQuantityError,
    StockQuantityArithmeticError,
)
from src.modules.inventory.domain.policy.stock_transfer_dispatch import (
    StockTransferDispatchPolicy,
)
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionTransferSnapshotError,
    InvalidStockExecutionValueError,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.issue_route import (
    IssueExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.internal_move_route import (
    InternalMoveExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.receipt_route import (
    ReceiptExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.error import (
    InvalidStockLocationSnapshotError,
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
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.entry_binding import (
    StockPostingEntryBindingVO,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_transfer.aggregate import StockTransfer
from src.modules.inventory.domain.stock_transfer.dispatch_snapshot import (
    StockTransferDispatchSnapshot,
)
from src.modules.inventory.domain.stock_transfer.error import (
    EmptyStockTransferError,
    InvalidStockTransferValueError,
    InvalidStockTransferLineError,
    InvalidStockTransferTransitError,
    InvalidStockTransferExecutionBindingError,
    InvalidStockTransferDispatchPlanSnapshotError,
    InvalidStockTransferDispatchSnapshotError,
    StockTransferDispatchMismatchError,
    StockTransferDispatchQuantityExceededError,
    StockTransferStatusError,
    StockTransferTimeError,
    StockTransferTransitMismatchError,
    StockTransferVersionConflictError,
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
from src.modules.inventory.domain.stock_transfer.value_object.transit import (
    StockTransferTransitVO,
)
from src.modules.inventory.domain.stock_transfer.value_object.execution_binding import (
    StockTransferExecutionBindingVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseSnapshotError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class StockTransferDispatchDomainTests(unittest.TestCase):
    """Проверяет оба факта отправки и собственный прогресс без предположения об атомарном сохранении."""

    def setUp(self) -> None:
        """Готовит план 50 KG, исходный запас 50, нулевой транзит и отправку 20 KG как расход 20 / приход 8+12."""
        self.f = transfer_fixture.StockTransferDomainTests()
        self.f.setUp()
        self.time = self.f.time
        self.transfer = self.f.confirm()
        self.transit_warehouse = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.source_location = StockLocationSnapshot(
            StockLocationIdVO(uuid4()), self.f.source.id, LocationType.STORAGE, True
        )
        self.transit_location = StockLocationSnapshot(
            StockLocationIdVO(uuid4()),
            self.transit_warehouse.id,
            LocationType.TRANSIT,
            True,
        )
        self.transit = StockTransferTransitVO(
            self.transit_warehouse.id, self.transit_location.id
        )
        self.source_dimensions = StockDimensionsVO(
            self.f.item.id,
            self.source_location.id,
            self.f.owner,
            None,
            None,
            StockStatus.SELLABLE,
        )
        self.transit_dimensions = replace(
            self.source_dimensions, location_id=self.transit_location.id
        )
        self.source_position = StockPosition.restore(
            identifier=StockPositionIdVO(uuid4()),
            dimensions=self.source_dimensions,
            base_uom=self.f.item.base_uom,
            on_hand_qty=QuantityVO(Decimal(50)),
            version=0,
        )
        self.transit_position = StockPosition.restore(
            identifier=StockPositionIdVO(uuid4()),
            dimensions=self.transit_dimensions,
            base_uom=self.f.item.base_uom,
            on_hand_qty=QuantityVO(Decimal(0)),
            version=0,
        )
        self.issue = self.fact(StockOperationType.ISSUE, ("20",))
        self.receipt = self.fact(StockOperationType.RECEIPT, ("8", "12"))

    def fact(
        self,
        operation: StockOperationType,
        amounts: tuple[str, ...],
        *,
        uom: str = "KG",
        **changes: object,
    ) -> StockExecution:
        """Восстанавливает полный собственный факт с реальными строками, сохранённым пересчётом и маршрутом."""
        issue = operation is StockOperationType.ISSUE
        dimensions = self.source_dimensions if issue else self.transit_dimensions
        route = (
            IssueExecutionRouteVO(dimensions)
            if issue
            else ReceiptExecutionRouteVO(dimensions)
        )
        lines = tuple(
            StockExecutionLine.create(
                identifier=StockExecutionLineIdVO(uuid4()),
                document_line_id=StockDocumentLineIdVO(uuid4()),
                inventory_item=self.f.item.execution_snapshot(),
                quantity=QuantityVO(Decimal(value)),
                uom=UomCodeVO(uom),
                route=route,
            )
            for value in amounts
        )
        return StockExecution.restore(
            **(
                dict(
                    identifier=StockExecutionIdVO(uuid4()),
                    document_id=StockDocumentIdVO(uuid4()),
                    document_version=0,
                    operation_type=operation,
                    warehouse_id=(
                        self.f.source.id if issue else self.transit_warehouse.id
                    ),
                    owner_id=self.f.owner,
                    executed_at=self.time,
                    lines=lines,
                )
                | changes
            )
        )

    def bindings(
        self, execution: StockExecution
    ) -> tuple[StockTransferExecutionBindingVO, ...]:
        """Назначает все фактические строки одной плановой строке, без отдельного количества."""
        return tuple(
            StockTransferExecutionBindingVO(line.id, self.f.line.id)
            for line in execution.lines
        )

    def build(self, **changes: object) -> StockTransferDispatchSnapshot:
        """Строит результат пары по текущему плану, маршруту и ровно участвующим локациям."""
        return StockTransferDispatchPolicy.build_dispatch(
            **(
                dict(
                    transfer=self.transfer.dispatch_snapshot(),
                    issue=self.issue.transfer_snapshot(),
                    receipt=self.receipt.transfer_snapshot(),
                    transit=self.transit,
                    source_warehouse=self.f.source,
                    destination_warehouse=self.f.destination,
                    transit_warehouse=self.transit_warehouse,
                    locations=(self.source_location, self.transit_location),
                    issue_bindings=self.bindings(self.issue),
                    receipt_bindings=self.bindings(self.receipt),
                )
                | changes
            )
        )

    def register(
        self,
        dispatch: object | None = None,
        transfer: StockTransfer | None = None,
        **changes: object,
    ) -> StockTransfer:
        """Применяет один результат пары одной следующей версией к выбранному состоянию плана."""
        transfer = self.transfer if transfer is None else transfer
        return transfer.register_dispatch(
            self.build() if dispatch is None else dispatch,
            **(dict(expected_version=transfer.version, updated_at=self.time) | changes),
        )

    def restore(self, reference: StockTransfer, **changes: object) -> StockTransfer:
        """Восстанавливает полный собственный прогресс и маршрут без текущего внешнего контекста."""
        return StockTransfer.restore(
            **(
                dict(
                    identifier=reference.id,
                    source_warehouse_id=reference.source_warehouse_id,
                    destination_warehouse_id=reference.destination_warehouse_id,
                    owner_id=reference.owner_id,
                    status=reference.status,
                    lines=reference.lines,
                    transit=reference.transit,
                    created_at=reference.created_at,
                    updated_at=reference.updated_at,
                    version=reference.version,
                )
                | changes
            )
        )

    def posting(
        self,
        execution: StockExecution,
        position: StockPosition,
        location: StockLocationSnapshot,
    ) -> StockPosting:
        """Строит одно существующее проведение по факту с общим для пары моментом учёта."""
        return StockPosting.create_from_execution(
            identifier=StockPostingIdVO(uuid4()),
            execution=execution.posting_snapshot(),
            inventory_items=(self.f.item.tracking_snapshot(),),
            posted_at=self.time,
            positions=(position.snapshot(),),
            locations=(location,),
            entry_bindings=(
                StockPostingEntryBindingVO(position.id, StockLedgerEntryIdVO(uuid4())),
            ),
        )

    def test_transit_and_binding_are_typed_immutable_value_objects(self) -> None:
        """VO проверяют свои ссылки; активность склада и назначение локации остаются внешней Policy."""
        with self.assertRaises(FrozenInstanceError):
            self.transit.location_id = self.source_location.id
        for changes in (dict(warehouse_id=uuid4()), dict(location_id=None)):
            with self.assertRaises(InvalidStockTransferTransitError):
                replace(self.transit, **changes)
        binding = self.bindings(self.issue)[0]
        for changes in (
            dict(execution_line_id=uuid4()),
            dict(transfer_line_id=self.f.item.id),
        ):
            with self.assertRaises(InvalidStockTransferExecutionBindingError):
                replace(binding, **changes)

    def test_producer_snapshots_are_frozen_minimal_and_validate_full_roots(
        self,
    ) -> None:
        """Снимки передают текущую версию и физические измерения, не полные корни или маршруты."""
        plan = self.transfer.dispatch_snapshot()
        fact = self.issue.transfer_snapshot()
        self.assertEqual(plan.lines[0].dispatched_qty.value, Decimal(0))
        self.assertEqual(fact.lines[0].dimensions, self.source_dimensions)
        self.assertFalse(hasattr(fact.lines[0], "conversion"))
        with self.assertRaises(FrozenInstanceError):
            fact.lines = ()
        with self.assertRaises(InvalidStockTransferValueError):
            replace(self.transfer, version=True).dispatch_snapshot()
        with self.assertRaises(InvalidStockExecutionValueError):
            replace(self.issue, document_version=True).transfer_snapshot()
        with self.assertRaises(InventoryError):
            replace(
                self.issue, lines=(replace(self.issue.lines[0], route=None),)
            ).transfer_snapshot()

    def test_balanced_pair_groups_different_splits_and_preserves_all_fact_ids(
        self,
    ) -> None:
        """Расход 20 и приход 8+12 формируют одну отправку 20 KG с ID всех целых строк."""
        result = self.build()
        self.assertEqual(
            (result.transfer_id, result.transfer_version, result.executed_at),
            (self.transfer.id, 2, self.time),
        )
        self.assertEqual(result.lines[0].quantity.value, Decimal(20))
        self.assertEqual(
            set(result.lines[0].issue_execution_line_ids),
            {line.id for line in self.issue.lines},
        )
        self.assertEqual(
            set(result.lines[0].receipt_execution_line_ids),
            {line.id for line in self.receipt.lines},
        )
        self.assertEqual(
            self.build(
                receipt_bindings=tuple(reversed(self.bindings(self.receipt))),
                receipt=replace(
                    self.receipt.transfer_snapshot(),
                    lines=tuple(reversed(self.receipt.transfer_snapshot().lines)),
                ),
            ),
            result,
        )

    def test_partial_and_full_dispatch_fix_route_but_do_not_complete_transfer(
        self,
    ) -> None:
        """20+30 KG исчерпывают отправку, но перемещение остаётся IN_PROGRESS до будущей приёмки."""
        partial = self.register()
        self.assertEqual(
            (partial.status, partial.version, partial.transit),
            (StockTransferStatus.IN_PROGRESS, 3, self.transit),
        )
        self.assertEqual(
            (
                partial.lines[0].dispatched_qty.value,
                partial.lines[0].remaining_to_dispatch_qty().value,
            ),
            (Decimal(20), Decimal(30)),
        )
        issue, receipt = self.fact(StockOperationType.ISSUE, ("30",)), self.fact(
            StockOperationType.RECEIPT, ("30",)
        )
        result = self.build(
            transfer=partial.dispatch_snapshot(),
            issue=issue.transfer_snapshot(),
            receipt=receipt.transfer_snapshot(),
            issue_bindings=self.bindings(issue),
            receipt_bindings=self.bindings(receipt),
        )
        full = self.register(result, partial)
        self.assertEqual(
            (full.status, full.version, full.lines[0].dispatched_qty.value),
            (StockTransferStatus.IN_PROGRESS, 4, Decimal(50)),
        )
        self.assertEqual(full.lines[0].remaining_to_dispatch_qty().value, Decimal(0))
        self.assertEqual(
            replace(full.lines[0], dispatched_qty=QuantityVO(Decimal(0))),
            self.transfer.lines[0],
        )
        self.assertEqual(self.transfer.lines[0].dispatched_qty.value, Decimal(0))

    def test_one_pair_can_dispatch_full_plan_without_claiming_receipt_at_destination(
        self,
    ) -> None:
        """Полная первая отправка переводит CONFIRMED в IN_PROGRESS с нулевой приёмкой без завершения перемещения."""
        issue, receipt = self.fact(StockOperationType.ISSUE, ("50",)), self.fact(
            StockOperationType.RECEIPT, ("50",)
        )
        result = self.build(
            issue=issue.transfer_snapshot(),
            receipt=receipt.transfer_snapshot(),
            issue_bindings=self.bindings(issue),
            receipt_bindings=self.bindings(receipt),
        )
        full = self.register(result)
        self.assertEqual(full.status, StockTransferStatus.IN_PROGRESS)
        self.assertEqual(full.lines[0].dispatched_qty, full.lines[0].planned_qty)
        self.assertEqual(full.lines[0].received_qty.value, Decimal(0))

    def test_unbalanced_totals_or_lot_status_composition_are_rejected(self) -> None:
        """Одинаковое общее количество не позволяет подменять LOT или состояние товара."""
        snapshot = self.receipt.transfer_snapshot()
        with self.assertRaises(UnbalancedStockTransferDispatchError):
            self.build(
                receipt=replace(
                    snapshot,
                    lines=(
                        replace(snapshot.lines[0], quantity=QuantityVO(Decimal(7))),
                        snapshot.lines[1],
                    ),
                )
            )
        for changes in (
            dict(lot_id=StockLotIdVO(uuid4())),
            dict(stock_status=StockStatus.DAMAGED),
        ):
            with self.assertRaises(UnbalancedStockTransferDispatchError):
                self.build(
                    receipt=replace(
                        snapshot,
                        lines=tuple(
                            replace(
                                line, dimensions=replace(line.dimensions, **changes)
                            )
                            for line in snapshot.lines
                        ),
                    )
                )

    def test_lot_balances_must_match_even_when_overall_total_is_equal(self) -> None:
        """Баланс проверяется отдельно по партиям, а не только по сумме одной плановой строки."""
        lot_a, lot_b = StockLotIdVO(uuid4()), StockLotIdVO(uuid4())
        issue = self.issue.transfer_snapshot()
        issue_a = replace(
            issue.lines[0],
            quantity=QuantityVO(Decimal(8)),
            dimensions=replace(issue.lines[0].dimensions, lot_id=lot_a),
        )
        issue_b = replace(
            issue.lines[0],
            id=StockExecutionLineIdVO(uuid4()),
            quantity=QuantityVO(Decimal(12)),
            dimensions=replace(issue.lines[0].dimensions, lot_id=lot_b),
        )
        issue = replace(issue, lines=(issue_a, issue_b))
        receipt = self.receipt.transfer_snapshot()
        receipt = replace(
            receipt,
            lines=(
                replace(
                    receipt.lines[0],
                    dimensions=replace(receipt.lines[0].dimensions, lot_id=lot_a),
                ),
                replace(
                    receipt.lines[1],
                    dimensions=replace(receipt.lines[1].dimensions, lot_id=lot_b),
                ),
            ),
        )
        bindings = tuple(
            StockTransferExecutionBindingVO(line.id, self.f.line.id)
            for line in issue.lines
        )
        self.assertEqual(
            self.build(issue=issue, receipt=receipt, issue_bindings=bindings)
            .lines[0]
            .quantity.value,
            Decimal(20),
        )
        wrong = replace(
            receipt,
            lines=(
                replace(receipt.lines[0], quantity=QuantityVO(Decimal(9))),
                replace(receipt.lines[1], quantity=QuantityVO(Decimal(11))),
            ),
        )
        with self.assertRaises(UnbalancedStockTransferDispatchError):
            self.build(issue=issue, receipt=wrong, issue_bindings=bindings)

    def test_all_rows_of_both_facts_are_assigned_once(self) -> None:
        """Не назначенная часть, лишняя ссылка и повторное назначение фактической строки запрещены."""
        original = self.bindings(self.receipt)
        for values in (
            (),
            original[:1],
            (*original, original[0]),
            (
                replace(original[0], execution_line_id=StockExecutionLineIdVO(uuid4())),
                original[1],
            ),
            (
                replace(original[0], transfer_line_id=StockTransferLineIdVO(uuid4())),
                original[1],
            ),
        ):
            with self.assertRaises(StockTransferDispatchMismatchError):
                self.build(receipt_bindings=values)
        for values in (None, [], (None,)):
            with self.assertRaises(InvalidStockTransferExecutionBindingError):
                self.build(issue_bindings=values)

    def test_individual_fact_item_or_base_unit_cannot_be_reinterpreted(self) -> None:
        """Плановая строка проверяется для каждого назначенного факта до группировки."""
        snapshot = self.receipt.transfer_snapshot()
        changed_item = replace(
            snapshot.lines[0].dimensions,
            inventory_item_id=type(self.f.item.id)(uuid4()),
        )
        with self.assertRaises(StockTransferDispatchMismatchError):
            self.build(
                receipt=replace(
                    snapshot,
                    lines=(
                        replace(
                            snapshot.lines[0],
                            inventory_item_id=changed_item.inventory_item_id,
                            dimensions=changed_item,
                        ),
                        snapshot.lines[1],
                    ),
                )
            )
        with self.assertRaises(StockTransferDispatchMismatchError):
            self.build(
                receipt=replace(
                    snapshot,
                    lines=(
                        replace(snapshot.lines[0], base_uom=UomCodeVO("G")),
                        snapshot.lines[1],
                    ),
                )
            )

    def test_pair_requires_issue_from_source_and_receipt_to_transit_of_same_owner(
        self,
    ) -> None:
        """Две стороны не могут меняться ролями, складом или владельцем."""
        for changes in (
            dict(operation_type=StockOperationType.RECEIPT),
            dict(warehouse_id=self.f.destination.id),
        ):
            with self.assertRaises(StockTransferDispatchMismatchError):
                self.build(issue=replace(self.issue.transfer_snapshot(), **changes))
        for changes in (
            dict(operation_type=StockOperationType.ISSUE),
            dict(warehouse_id=self.f.source.id),
        ):
            with self.assertRaises(StockTransferDispatchMismatchError):
                self.build(receipt=replace(self.receipt.transfer_snapshot(), **changes))
        snapshot = self.issue.transfer_snapshot()
        owner = StockOwnerIdVO(uuid4())
        with self.assertRaises(StockTransferDispatchMismatchError):
            self.build(
                issue=replace(
                    snapshot,
                    owner_id=owner,
                    lines=tuple(
                        replace(
                            line, dimensions=replace(line.dimensions, owner_id=owner)
                        )
                        for line in snapshot.lines
                    ),
                )
            )
        with self.assertRaises(StockTransferDispatchMismatchError):
            self.build(
                receipt=replace(self.receipt.transfer_snapshot(), id=self.issue.id)
            )
        with self.assertRaises(StockTransferDispatchMismatchError):
            self.build(
                receipt=replace(
                    self.receipt.transfer_snapshot(),
                    lines=(
                        replace(
                            self.receipt.transfer_snapshot().lines[0],
                            id=self.issue.lines[0].id,
                        ),
                        self.receipt.transfer_snapshot().lines[1],
                    ),
                )
            )

    def test_three_warehouses_and_locations_are_current_active_and_exact(self) -> None:
        """Перед отправкой проверяются оба конечных склада, транзит и фактические активные локации."""
        for field, warehouse in (
            ("source_warehouse", self.f.source),
            ("destination_warehouse", self.f.destination),
            ("transit_warehouse", self.transit_warehouse),
        ):
            with self.assertRaises(WarehouseInactiveError):
                self.build(**{field: replace(warehouse, is_active=False)})
            with self.assertRaises(InvalidWarehouseSnapshotError):
                self.build(**{field: None})
        with self.assertRaises(StockTransferTransitMismatchError):
            self.build(transit_warehouse=self.f.destination)
        for locations in (
            (),
            (self.source_location,),
            (self.source_location, self.transit_location, self.source_location),
        ):
            with self.assertRaises(StockTransferDispatchMismatchError):
                self.build(locations=locations)
        for locations in ([], None, (None,)):
            with self.assertRaises(InvalidStockLocationSnapshotError):
                self.build(locations=locations)
        with self.assertRaises(StockLocationInactiveError):
            self.build(
                locations=(
                    replace(self.source_location, is_active=False),
                    self.transit_location,
                )
            )
        with self.assertRaises(StockLocationWarehouseMismatchError):
            self.build(
                locations=(
                    replace(self.source_location, warehouse_id=self.f.destination.id),
                    self.transit_location,
                )
            )

    def test_transit_must_be_separate_and_receipt_goes_only_to_selected_transit_location(
        self,
    ) -> None:
        """Локация хранения или другой транзит не подменяют выбранную буферную позицию."""
        for warehouse_id in (self.f.source.id, self.f.destination.id):
            with self.assertRaises(StockTransferTransitMismatchError):
                self.build(transit=replace(self.transit, warehouse_id=warehouse_id))
        with self.assertRaises(StockTransferTransitMismatchError):
            self.build(
                transit=replace(self.transit, location_id=StockLocationIdVO(uuid4()))
            )
        with self.assertRaises(StockTransferTransitMismatchError):
            self.build(
                locations=(
                    self.source_location,
                    replace(self.transit_location, location_type=LocationType.STORAGE),
                )
            )
        with self.assertRaises(StockLocationInactiveError):
            self.build(
                locations=(
                    self.source_location,
                    replace(self.transit_location, is_active=False),
                )
            )

    def test_route_is_fixed_by_first_dispatch_and_cannot_be_changed(self) -> None:
        """Последующие факты используют тот же транзит; подмена отклоняется и корнем, и Policy."""
        partial = self.register()
        different = replace(self.transit, location_id=StockLocationIdVO(uuid4()))
        with self.assertRaises(StockTransferTransitMismatchError):
            self.build(transfer=partial.dispatch_snapshot(), transit=different)
        result = replace(
            self.build(), transfer_version=partial.version, transit=different
        )
        with self.assertRaises(StockTransferTransitMismatchError):
            self.register(result, partial)

    def test_cumulative_quantity_cannot_exceed_plan(self) -> None:
        """Проверяется накопленный прогресс и суммарное количество, а не размер отдельной фактической строки."""
        partial = self.register()
        with self.assertRaises(StockTransferDispatchQuantityExceededError):
            self.register(
                replace(
                    self.build(),
                    transfer_version=3,
                    lines=(
                        replace(
                            self.build().lines[0], quantity=QuantityVO(Decimal(31))
                        ),
                    ),
                ),
                partial,
            )
        issue, receipt = self.fact(StockOperationType.ISSUE, ("51",)), self.fact(
            StockOperationType.RECEIPT, ("51",)
        )
        with self.assertRaises(StockTransferDispatchQuantityExceededError):
            self.build(
                issue=issue.transfer_snapshot(),
                receipt=receipt.transfer_snapshot(),
                issue_bindings=self.bindings(issue),
                receipt_bindings=self.bindings(receipt),
            )

    def test_versions_are_strict_and_conflict_precedes_policy_and_history(self) -> None:
        """Версия команды проверяется раньше арифметики; подготовленный результат связан с текущей версией."""
        result = self.build()
        for value in (True, False, -1, "2", Decimal(2), None):
            with self.assertRaises(InvalidStockTransferValueError):
                self.register(result, expected_version=value)
        with patch.object(
            StockTransferDispatchPolicy,
            "ensure_compatible",
            side_effect=RuntimeError("must not run"),
        ):
            with self.assertRaises(StockTransferVersionConflictError):
                self.register(result, expected_version=1)
            with self.assertRaises(InvalidStockTransferValueError):
                self.register(
                    result, replace(self.transfer, version=True), expected_version=2
                )
        partial = self.register(result)
        with self.assertRaises(StockTransferVersionConflictError):
            self.register(result, partial)

    def test_dispatch_matches_root_identity_direction_owner_item_and_unit(self) -> None:
        """Повторная проверка результата защищает неизменяемые связи и область корня."""
        result = self.build()
        for changes in (
            dict(transfer_id=StockTransferIdVO(uuid4())),
            dict(source_warehouse_id=WarehouseIdVO(uuid4())),
            dict(destination_warehouse_id=WarehouseIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
        ):
            with self.assertRaises(StockTransferDispatchMismatchError):
                self.register(replace(result, **changes))
        for changes in (
            dict(transfer_line_id=StockTransferLineIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
        ):
            with self.assertRaises(StockTransferDispatchMismatchError):
                self.register(
                    replace(result, lines=(replace(result.lines[0], **changes),))
                )

    def test_pair_times_are_equal_and_registration_is_explicit_monotonic_utc(
        self,
    ) -> None:
        """Паре нужен один момент факта; регистрация не раньше факта или предыдущего состояния."""
        with self.assertRaises(StockTransferTimeError):
            self.build(
                receipt=replace(
                    self.receipt.transfer_snapshot(),
                    executed_at=self.time + timedelta(seconds=1),
                )
            )
        with self.assertRaises(StockTransferTimeError):
            self.build(
                transfer=replace(
                    self.transfer.dispatch_snapshot(),
                    updated_at=self.time + timedelta(seconds=1),
                )
            )
        for value in (
            None,
            "now",
            self.time.replace(tzinfo=None),
            self.time - timedelta(seconds=1),
        ):
            with self.assertRaises(StockTransferTimeError):
                self.register(updated_at=value)
        with self.assertRaises(StockTransferTimeError):
            self.register(
                replace(self.build(), executed_at=self.time + timedelta(seconds=1))
            )
        later = self.time + timedelta(minutes=1)
        self.assertEqual(
            self.register(
                updated_at=later.astimezone(timezone(timedelta(hours=2)))
            ).updated_at,
            later,
        )

    def test_only_confirmed_or_in_progress_accept_dispatch_and_progress_cannot_be_edited(
        self,
    ) -> None:
        """Черновик/отмена не принимают факты; отправленный план не открывает отмену и редактирование."""
        for transfer in (self.f.add(), self.f.cancel(self.f.add())):
            with self.assertRaises(StockTransferStatusError):
                self.build(transfer=transfer.dispatch_snapshot())
            with self.assertRaises(StockTransferStatusError):
                self.register(self.build(), transfer)
        partial = self.register()
        for operation in (
            self.f.add,
            self.f.change,
            self.f.remove,
            self.f.confirm,
            self.f.cancel,
        ):
            with self.assertRaises(StockTransferStatusError):
                operation(partial)

    def test_restore_validates_status_progress_route_and_preserves_history(
        self,
    ) -> None:
        """Историческая отправка восстанавливается без текущих складов и коэффициентов, но требует согласованный состав."""
        partial = self.register()
        self.assertEqual(self.restore(partial), partial)
        historical = replace(
            partial.lines[0],
            planned_qty=QuantityVO(Decimal(100)),
            conversion=replace(
                partial.lines[0].conversion, factor_to_base=Decimal("0.002")
            ),
        )
        self.assertEqual(
            self.restore(partial, lines=(historical,)).lines[0], historical
        )
        for changes in (
            dict(transit=None),
            dict(status=StockTransferStatus.CONFIRMED),
            dict(
                lines=(
                    replace(partial.lines[0], dispatched_qty=QuantityVO(Decimal(0))),
                )
            ),
            dict(transit="bad"),
        ):
            with self.assertRaises(InvalidStockTransferValueError):
                self.restore(partial, **changes)
        with self.assertRaises(StockTransferTransitMismatchError):
            self.restore(
                partial, transit=replace(self.transit, warehouse_id=self.f.source.id)
            )
        with self.assertRaises(EmptyStockTransferError):
            self.restore(partial, lines=())
        with self.assertRaises(StockTransferDispatchQuantityExceededError):
            replace(
                partial.lines[0], dispatched_qty=QuantityVO(Decimal(51))
            ).ensure_valid()
        with self.assertRaises(InvalidStockTransferLineError):
            replace(partial.lines[0], dispatched_qty=None).ensure_valid()

    def test_specialized_snapshot_contracts_are_required(self) -> None:
        """Полные корни и снимки других назначений не заменяют контракты новой Policy."""
        for value in (None, self.transfer, self.f.item.stock_snapshot()):
            with self.assertRaises(InvalidStockTransferDispatchPlanSnapshotError):
                self.build(transfer=value)
        for value in (None, self.issue, self.issue.posting_snapshot()):
            with self.assertRaises(InvalidStockExecutionTransferSnapshotError):
                self.build(issue=value)
        with self.assertRaises(InvalidStockTransferTransitError):
            self.build(transit=None)
        with self.assertRaises(InvalidStockTransferDispatchSnapshotError):
            self.register(self.issue.transfer_snapshot())

    def test_snapshots_revalidate_types_versions_and_unique_fact_ids(self) -> None:
        """Потребители проверяют frozen-снимки повторно, включая bool-версию, UTC и повторы."""
        plan = self.transfer.dispatch_snapshot()
        for changes in (
            dict(id=uuid4()),
            dict(version=True),
            dict(status="CONFIRMED"),
            dict(transit="bad"),
            dict(updated_at=self.time.replace(tzinfo=None)),
            dict(lines=[]),
            dict(lines=(plan.lines[0], plan.lines[0])),
            dict(status=StockTransferStatus.IN_PROGRESS),
        ):
            with self.assertRaises(InvalidStockTransferDispatchPlanSnapshotError):
                self.build(transfer=replace(plan, **changes))
        result = self.build()
        for changes in (
            dict(transfer_id=uuid4()),
            dict(transfer_version=True),
            dict(transit=None),
            dict(issue_execution_id=result.receipt_execution_id),
            dict(executed_at=self.time.replace(tzinfo=None)),
            dict(lines=()),
            dict(lines=[]),
            dict(lines=(result.lines[0], result.lines[0])),
        ):
            with self.assertRaises(InvalidStockTransferDispatchSnapshotError):
                self.register(replace(result, **changes))
        for changes in (
            dict(quantity=QuantityVO(Decimal(0))),
            dict(issue_execution_line_ids=()),
            dict(receipt_execution_line_ids=[]),
            dict(receipt_execution_line_ids=result.lines[0].issue_execution_line_ids),
        ):
            with self.assertRaises(InvalidStockTransferDispatchSnapshotError):
                self.register(
                    replace(result, lines=(replace(result.lines[0], **changes),))
                )
        fact = self.issue.transfer_snapshot()
        for changes in (
            dict(id=uuid4()),
            dict(operation_type=StockOperationType.INTERNAL_MOVE),
            dict(owner_id=None),
            dict(executed_at=self.time.replace(tzinfo=None)),
            dict(lines=()),
            dict(lines=(fact.lines[0], fact.lines[0])),
        ):
            with self.assertRaises(InvalidStockExecutionTransferSnapshotError):
                self.build(issue=replace(fact, **changes))

    def test_serial_identity_is_conserved_and_repeated_instances_are_rejected(
        self,
    ) -> None:
        """Пара индивидуальных PCS сохраняет конкретные серийные ID, без объединения разных экземпляров."""
        serial = StockSerialIdVO(uuid4())
        plan = self.transfer.dispatch_snapshot()
        plan = replace(plan, lines=(replace(plan.lines[0], base_uom=UomCodeVO("PCS")),))
        issue = self.issue.transfer_snapshot()
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
        receipt = self.receipt.transfer_snapshot()
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
        receipt_bindings = (
            StockTransferExecutionBindingVO(receipt.lines[0].id, self.f.line.id),
        )
        self.assertEqual(
            self.build(
                transfer=plan,
                issue=issue,
                receipt=receipt,
                receipt_bindings=receipt_bindings,
            )
            .lines[0]
            .quantity.value,
            Decimal(1),
        )
        with self.assertRaises(UnbalancedStockTransferDispatchError):
            self.build(
                transfer=plan,
                issue=issue,
                receipt=replace(
                    receipt,
                    lines=(
                        replace(
                            receipt.lines[0],
                            dimensions=replace(
                                receipt.lines[0].dimensions,
                                serial_id=StockSerialIdVO(uuid4()),
                            ),
                        ),
                    ),
                ),
                receipt_bindings=receipt_bindings,
            )
        with self.assertRaises(InvalidStockExecutionTransferSnapshotError):
            self.build(
                issue=replace(
                    issue,
                    lines=(replace(issue.lines[0], quantity=QuantityVO(Decimal(2))),),
                )
            )
        with self.assertRaises(InvalidStockExecutionTransferSnapshotError):
            self.build(
                issue=replace(
                    issue,
                    lines=(
                        issue.lines[0],
                        replace(issue.lines[0], id=StockExecutionLineIdVO(uuid4())),
                    ),
                )
            )

    def test_two_existing_postings_preserve_owner_total_and_transit_is_unavailable(
        self,
    ) -> None:
        """Два проведения с общей датой дают A=30/T=20, сумму 50 и нулевую пригодность транзита."""
        dispatch = self.build()
        outgoing = self.posting(self.issue, self.source_position, self.source_location)
        incoming = self.posting(
            self.receipt, self.transit_position, self.transit_location
        )
        self.assertEqual(outgoing.posted_at, incoming.posted_at)
        a = self.source_position.apply_posting_entry(
            outgoing.entries[0].snapshot(),
            expected_version=0,
            inventory_item=self.f.item.stock_snapshot(),
            location=self.source_location,
            warehouse=self.f.source,
        )
        transit = self.transit_position.apply_posting_entry(
            incoming.entries[0].snapshot(),
            expected_version=0,
            inventory_item=self.f.item.stock_snapshot(),
            location=self.transit_location,
            warehouse=self.transit_warehouse,
        )
        transfer = self.register(dispatch)
        self.assertEqual(
            (
                a.on_hand_qty.value,
                transit.on_hand_qty.value,
                transfer.lines[0].dispatched_qty.value,
            ),
            (Decimal(30), Decimal(20), Decimal(20)),
        )
        self.assertEqual(a.on_hand_qty.value + transit.on_hand_qty.value, Decimal(50))
        pool = AvailabilityPool.create(
            identifier=AvailabilityPoolIdVO(uuid4()),
            key=AvailabilityPoolKeyVO(
                self.f.item.id, self.transit_warehouse.id, self.f.owner
            ),
            inventory_item=self.f.item.availability_snapshot(),
            warehouse=self.transit_warehouse,
            as_of=self.time.date(),
            positions=(transit.availability_snapshot(),),
            locations=(self.transit_location,),
        )
        self.assertEqual(pool.eligible_qty.value, Decimal(0))
        self.assertEqual(transit.dimensions.stock_status, StockStatus.SELLABLE)
        self.assertEqual(
            (
                self.source_position.on_hand_qty.value,
                self.transit_position.on_hand_qty.value,
            ),
            (Decimal(50), Decimal(0)),
        )

    def test_insufficient_source_stock_rejects_physical_candidate_without_changing_roots(
        self,
    ) -> None:
        """Корректная пара не подменяет проверку остатка позиции; несохранённые кандидаты остаются независимыми."""
        source = replace(self.source_position, on_hand_qty=QuantityVO(Decimal(10)))
        posting = self.posting(self.issue, source, self.source_location)
        candidate = self.register()
        with self.assertRaises(NegativeStockQuantityError):
            source.apply_posting_entry(
                posting.entries[0].snapshot(),
                expected_version=0,
                inventory_item=self.f.item.stock_snapshot(),
                location=self.source_location,
                warehouse=self.f.source,
            )
        self.assertEqual(self.transfer.status, StockTransferStatus.CONFIRMED)
        self.assertEqual(candidate.status, StockTransferStatus.IN_PROGRESS)
        self.assertEqual(source.on_hand_qty.value, Decimal(10))

    def test_gram_input_and_hostile_context_do_not_round_balance(self) -> None:
        """Обе стороны используют базовые количества без повторного пересчёта пользовательского ввода."""
        issue = self.fact(StockOperationType.ISSUE, ("20000",), uom="G")
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            result = self.build(
                issue=issue.transfer_snapshot(), issue_bindings=self.bindings(issue)
            )
            self.assertEqual(result.lines[0].quantity.value, Decimal(20))
            self.assertEqual(
                self.register(result).lines[0].remaining_to_dispatch_qty().value,
                Decimal(30),
            )

    def test_large_dense_group_sum_has_controlled_arithmetic_failure(self) -> None:
        """Защитный предел общей арифметики не обходится при группировке отправки."""
        issue = self.issue.transfer_snapshot()
        large = replace(issue.lines[0], quantity=QuantityVO(Decimal("1E+1000001")))
        small = replace(
            issue.lines[0],
            id=StockExecutionLineIdVO(uuid4()),
            quantity=QuantityVO(Decimal(1)),
        )
        bindings = tuple(
            StockTransferExecutionBindingVO(line.id, self.f.line.id)
            for line in (large, small)
        )
        with self.assertRaises(StockQuantityArithmeticError):
            self.build(
                issue=replace(issue, lines=(large, small)), issue_bindings=bindings
            )

    def test_local_versions_do_not_claim_global_pair_deduplication(self) -> None:
        """Старый результат отклоняется, но повторная сборка тех же фактов по новой версии требует внешнего журнала."""
        first = self.build()
        partial = self.register(first)
        with self.assertRaises(StockTransferVersionConflictError):
            self.register(first, partial)
        rebuilt = self.build(transfer=partial.dispatch_snapshot())
        self.assertEqual(
            self.register(rebuilt, partial).lines[0].dispatched_qty.value, Decimal(40)
        )

    def test_same_item_cannot_be_reassigned_between_different_transfer_lines(
        self,
    ) -> None:
        """Баланс включает ID строки плана: одинаковый товар не разрешает переставить приход между обязательствами."""
        second = self.f.new_line()
        transfer = self.f.confirm(self.f.add(self.f.add(), second))
        bindings = self.bindings(self.receipt)
        with self.assertRaises(UnbalancedStockTransferDispatchError):
            self.build(
                transfer=transfer.dispatch_snapshot(),
                receipt_bindings=(
                    bindings[0],
                    replace(bindings[1], transfer_line_id=second.id),
                ),
            )

    def test_different_source_locations_can_converge_to_one_transit_location(
        self,
    ) -> None:
        """Отбор из нескольких адресов сохраняет LOT/SERIAL/состояние, но не требует совпадения количества строк."""
        second_location = replace(self.source_location, id=StockLocationIdVO(uuid4()))
        issue = self.issue.transfer_snapshot()
        first = replace(issue.lines[0], quantity=QuantityVO(Decimal(8)))
        second = replace(
            issue.lines[0],
            id=StockExecutionLineIdVO(uuid4()),
            quantity=QuantityVO(Decimal(12)),
            dimensions=replace(self.source_dimensions, location_id=second_location.id),
        )
        issue = replace(issue, lines=(first, second))
        receipt = self.receipt.transfer_snapshot()
        receipt = replace(
            receipt,
            lines=(replace(receipt.lines[0], quantity=QuantityVO(Decimal(20))),),
        )
        dispatch = self.build(
            issue=issue,
            receipt=receipt,
            locations=(self.source_location, second_location, self.transit_location),
            issue_bindings=tuple(
                StockTransferExecutionBindingVO(line.id, self.f.line.id)
                for line in issue.lines
            ),
            receipt_bindings=(
                StockTransferExecutionBindingVO(receipt.lines[0].id, self.f.line.id),
            ),
        )
        self.assertEqual(
            (
                dispatch.lines[0].quantity.value,
                len(dispatch.lines[0].issue_execution_line_ids),
                len(dispatch.lines[0].receipt_execution_line_ids),
            ),
            (Decimal(20), 2, 1),
        )

    def test_internal_move_cannot_be_exported_as_one_side_of_transfer_pair(
        self,
    ) -> None:
        """Существующий внутренний маршрут остаётся самостоятельным и не теряет одну сторону в новом снимке."""
        route = InternalMoveExecutionRouteVO(
            self.source_dimensions,
            replace(self.source_dimensions, location_id=StockLocationIdVO(uuid4())),
        )
        execution = replace(
            self.issue,
            operation_type=StockOperationType.INTERNAL_MOVE,
            lines=(replace(self.issue.lines[0], route=route),),
        )
        with self.assertRaises(InvalidStockExecutionTransferSnapshotError):
            execution.transfer_snapshot()


if __name__ == "__main__":
    unittest.main()
