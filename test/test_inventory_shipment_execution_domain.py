"""Регистрация частичной и полной отгрузки по фактическим строкам и её связь с погашением резервов."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from itertools import permutations
from unittest.mock import patch
from uuid import uuid4

from test import test_inventory_shipment_domain as shipment_fixture

from src.modules.inventory.domain.error import (
    StockQuantityArithmeticError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.shipment_execution import (
    ShipmentExecutionPolicy,
)
from src.modules.inventory.domain.policy.stock_execution_reservation import (
    StockExecutionReservationPolicy,
)
from src.modules.inventory.domain.shipment.aggregate import Shipment
from src.modules.inventory.domain.shipment.entity.shipment_line import ShipmentLine
from src.modules.inventory.domain.shipment.error import (
    EmptyShipmentError,
    InvalidShipmentExecutionBindingError,
    InvalidShipmentExecutionPlanSnapshotError,
    InvalidShipmentExecutionRegistrationSnapshotError,
    InvalidShipmentLineError,
    InvalidShipmentValueError,
    ShipmentExecutionMismatchError,
    ShipmentQuantityExceededError,
    ShipmentStatusError,
    ShipmentTimeError,
    ShipmentVersionConflictError,
)
from src.modules.inventory.domain.shipment.registration_snapshot import (
    ShipmentExecutionRegistrationSnapshot,
)
from src.modules.inventory.domain.shipment.value_object.execution_binding import (
    ShipmentExecutionBindingVO,
)
from src.modules.inventory.domain.shipment.value_object.identifier import ShipmentIdVO
from src.modules.inventory.domain.shipment.value_object.line_id import ShipmentLineIdVO
from src.modules.inventory.domain.shipment.value_object.status import ShipmentStatus
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.entity.stock_execution_line import (
    StockExecutionLine,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionReservationSnapshotError,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.issue_route import (
    IssueExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
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
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_reservation.error import (
    StockReservationConsumptionExceededError,
    StockReservationExpiredError,
)
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.status import (
    StockReservationStatus,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class ShipmentExecutionDomainTests(unittest.TestCase):
    """Проверяет собственный прогресс, назначения целых фактических строк и границы согласованности."""

    def setUp(self) -> None:
        """Готовит подтверждённые 3+2 KG, удержания 4+3 KG и фактический расход 1+1+1 KG."""
        self.fixture = shipment_fixture.ShipmentDomainTests()
        self.fixture.setUp()
        f = self.fixture
        self.shipment = f.confirm(f.draft())
        self.time = f.time
        self.location = StockLocationSnapshot(
            StockLocationIdVO(uuid4()), f.warehouse.id, LocationType.STORAGE, True
        )
        self.position = StockPosition.restore(
            identifier=StockPositionIdVO(uuid4()),
            dimensions=StockDimensionsVO(
                f.item.id, self.location.id, f.owner, None, None, StockStatus.SELLABLE
            ),
            base_uom=f.item.base_uom,
            on_hand_qty=QuantityVO(Decimal(10)),
            version=0,
        )
        self.execution = self.fact(("1", "1", "1"))
        self.bindings = (
            ShipmentExecutionBindingVO(self.execution.lines[0].id, f.line_a.id),
            ShipmentExecutionBindingVO(self.execution.lines[1].id, f.line_a.id),
            ShipmentExecutionBindingVO(self.execution.lines[2].id, f.line_b.id),
        )

    def fact(
        self, amounts: tuple[str, ...], *, uom: str = "KG", **changes: object
    ) -> StockExecution:
        """Создаёт полный исторический факт с реальными строками, пересчётом и физическим маршрутом."""
        f = self.fixture
        lines = tuple(
            StockExecutionLine.create(
                identifier=StockExecutionLineIdVO(uuid4()),
                document_line_id=StockDocumentLineIdVO(uuid4()),
                inventory_item=f.item.execution_snapshot(),
                quantity=QuantityVO(Decimal(amount)),
                uom=UomCodeVO(uom),
                route=IssueExecutionRouteVO(self.position.dimensions),
            )
            for amount in amounts
        )
        return StockExecution.restore(
            **(
                dict(
                    identifier=StockExecutionIdVO(uuid4()),
                    document_id=StockDocumentIdVO(uuid4()),
                    document_version=0,
                    operation_type=StockOperationType.ISSUE,
                    warehouse_id=f.warehouse.id,
                    owner_id=f.owner,
                    executed_at=self.time,
                    lines=lines,
                )
                | changes
            )
        )

    def build(self, **changes: object) -> ShipmentExecutionRegistrationSnapshot:
        """Строит результат по специализированным снимкам без отдельного ввода количества."""
        return ShipmentExecutionPolicy.build_registration(
            **(
                dict(
                    shipment=self.shipment.execution_snapshot(),
                    execution=self.execution.reservation_snapshot(),
                    bindings=self.bindings,
                )
                | changes
            )
        )

    def register(
        self, registration: object | None = None, **changes: object
    ) -> Shipment:
        """Применяет результат одной версией к исходному подтверждённому плану."""
        return self.shipment.register_execution(
            self.build() if registration is None else registration,
            **(
                dict(expected_version=self.shipment.version, updated_at=self.time)
                | changes
            ),
        )

    def restore(self, shipment: Shipment, **changes: object) -> Shipment:
        """Восстанавливает полный собственный состав с явно переданной историей прогресса."""
        return Shipment.restore(
            **(
                dict(
                    identifier=shipment.id,
                    order_ref=shipment.order_ref,
                    warehouse_id=shipment.warehouse_id,
                    owner_id=shipment.owner_id,
                    status=shipment.status,
                    lines=shipment.lines,
                    created_at=shipment.created_at,
                    updated_at=shipment.updated_at,
                    version=shipment.version,
                    fulfillment_source=shipment.fulfillment_source,
                )
                | changes
            )
        )

    def test_new_lines_have_zero_progress_and_exact_remaining(self) -> None:
        """Создание начинает с нуля; остаток вычисляется, а восстановление требует полный прогресс."""
        line = self.shipment.lines[0]
        self.assertEqual(line.shipped_qty.value, Decimal(0))
        self.assertEqual(line.remaining_qty(), line.planned_qty)
        partial = replace(line, shipped_qty=QuantityVO(Decimal("1.05")))
        self.assertEqual(partial.remaining_qty().value, Decimal("1.95"))
        self.assertEqual(
            set(line.__dataclass_fields__),
            {
                "id",
                "source_ref",
                "reservation_id",
                "inventory_item_id",
                "base_uom",
                "planned_qty",
                "conversion",
                "shipped_qty",
                "fulfillment_allocation_id",
            },
        )
        for value in (None, Decimal(0), 0):
            with self.assertRaises(InvalidShipmentLineError):
                replace(line, shipped_qty=value).ensure_valid()
        with self.assertRaises(ShipmentQuantityExceededError):
            replace(line, shipped_qty=QuantityVO(Decimal("3.05"))).remaining_qty()

    def test_binding_has_only_typed_ids_and_is_immutable(self) -> None:
        """Назначение не позволяет отдельно задавать количество или выбирать резерв."""
        binding = self.bindings[0]
        self.assertEqual(
            set(binding.__dataclass_fields__), {"execution_line_id", "shipment_line_id"}
        )
        for changes in (
            dict(execution_line_id=uuid4()),
            dict(shipment_line_id=uuid4()),
            dict(shipment_line_id=self.fixture.a.id),
        ):
            with self.assertRaises(InvalidShipmentExecutionBindingError):
                replace(binding, **changes)
        with self.assertRaises(FrozenInstanceError):
            binding.shipment_line_id = self.fixture.line_b.id

    def test_plan_getter_is_specialized_frozen_and_revalidates_source(self) -> None:
        """Снимок содержит текущие остатки плана и версию, не чужой корень или коллекцию истории."""
        snapshot = self.shipment.execution_snapshot()
        snapshot.ensure_valid()
        self.assertEqual(snapshot.version, 3)
        self.assertEqual(snapshot.lines[0].reservation_id, self.fixture.a.id)
        self.assertFalse(hasattr(snapshot, "order"))
        self.assertFalse(hasattr(snapshot, "conversion"))
        with self.assertRaises(FrozenInstanceError):
            snapshot.version = 0
        with self.assertRaises(InvalidShipmentValueError):
            replace(self.shipment, version=True).execution_snapshot()

    def test_multiple_facts_for_one_plan_line_are_grouped_and_sorted(self) -> None:
        """Две физические строки дают одну сумму плана с сохранением всех фактических ID."""
        result = self.build()
        by_line = {line.shipment_line_id: line for line in result.lines}
        a = by_line[self.fixture.line_a.id]
        self.assertEqual(a.quantity.value, Decimal(2))
        self.assertEqual(a.reservation_id, self.fixture.a.id)
        self.assertEqual(
            set(a.execution_line_ids), {line.id for line in self.execution.lines[:2]}
        )
        self.assertEqual(by_line[self.fixture.line_b.id].quantity.value, Decimal(1))
        for values in permutations(self.bindings):
            self.assertEqual(self.build(bindings=values), result)
        self.assertEqual(
            self.build(
                execution=replace(
                    self.execution.reservation_snapshot(),
                    lines=tuple(reversed(self.execution.reservation_snapshot().lines)),
                )
            ),
            result,
        )

    def test_partial_then_full_progress_preserves_original_plan_and_bindings(
        self,
    ) -> None:
        """Последовательные 2+1 и 1+1 KG завершают план 3+2 KG двумя версиями."""
        partial = self.register()
        self.assertEqual(
            (partial.status, partial.version), (ShipmentStatus.PARTIALLY_SHIPPED, 4)
        )
        self.assertEqual(
            tuple(line.shipped_qty.value for line in partial.lines),
            (Decimal(2), Decimal(1)),
        )
        self.assertEqual(
            tuple(line.remaining_qty().value for line in partial.lines),
            (Decimal(1), Decimal(1)),
        )
        second = self.fact(("1", "1"))
        registration = self.build(
            shipment=partial.execution_snapshot(),
            execution=second.reservation_snapshot(),
            bindings=tuple(
                ShipmentExecutionBindingVO(actual.id, target.id)
                for actual, target in zip(second.lines, partial.lines)
            ),
        )
        full = partial.register_execution(
            registration, expected_version=4, updated_at=self.time
        )
        self.assertEqual((full.status, full.version), (ShipmentStatus.SHIPPED, 5))
        self.assertTrue(
            all(line.remaining_qty().value.is_zero() for line in full.lines)
        )
        for old, new in zip(self.shipment.lines, full.lines):
            self.assertEqual(replace(new, shipped_qty=old.shipped_qty), old)
        self.assertEqual(self.shipment.status, ShipmentStatus.CONFIRMED)
        self.assertTrue(
            all(line.shipped_qty.value.is_zero() for line in self.shipment.lines)
        )

    def test_full_progress_can_be_registered_in_one_fact(self) -> None:
        """CONFIRMED напрямую становится SHIPPED при точном полном исполнении."""
        execution = self.fact(("3", "2"))
        registration = self.build(
            execution=execution.reservation_snapshot(),
            bindings=tuple(
                ShipmentExecutionBindingVO(actual.id, target.id)
                for actual, target in zip(execution.lines, self.shipment.lines)
            ),
        )
        self.assertEqual(self.register(registration).status, ShipmentStatus.SHIPPED)

    def test_unselected_rows_are_neither_shipped_nor_bound_to_reservations(
        self,
    ) -> None:
        """Непривязанный физический расход не включается в прогресс и производные назначения резервов."""
        registration = self.build(bindings=self.bindings[:1])
        after = self.register(registration)
        self.assertEqual(
            tuple(line.shipped_qty.value for line in after.lines),
            (Decimal(1), Decimal(0)),
        )
        self.assertEqual(len(registration.reservation_bindings()), 1)
        self.assertEqual(
            registration.reservation_bindings()[0].execution_line_id,
            self.execution.lines[0].id,
        )

    def test_whole_execution_line_cannot_be_split_or_assigned_twice(self) -> None:
        """Для части строки нужно отдельное физическое исполнение; две привязки одной строки запрещены."""
        for extra in (
            self.bindings[0],
            replace(self.bindings[0], shipment_line_id=self.fixture.line_b.id),
        ):
            with self.assertRaises(ShipmentExecutionMismatchError):
                self.build(bindings=(*self.bindings, extra))

    def test_missing_raw_and_empty_bindings_are_rejected(self) -> None:
        """Назначения обязательны, типизированы и ссылаются на известные строки обоих источников."""
        for bindings in ((), [], None, (None,), (self.bindings[0].execution_line_id,)):
            with self.assertRaises(InvalidShipmentExecutionBindingError):
                self.build(bindings=bindings)
        for binding in (
            replace(
                self.bindings[0], execution_line_id=StockExecutionLineIdVO(uuid4())
            ),
            replace(self.bindings[0], shipment_line_id=ShipmentLineIdVO(uuid4())),
        ):
            with self.assertRaises(ShipmentExecutionMismatchError):
                self.build(bindings=(binding,))

    def test_only_issue_same_warehouse_and_owner_are_accepted(self) -> None:
        """Приход, перемещение и расход чужой области не исполняют собственную отгрузку."""
        snapshot = self.execution.reservation_snapshot()
        for changes in (
            dict(operation_type=StockOperationType.RECEIPT),
            dict(operation_type=StockOperationType.INTERNAL_MOVE),
            dict(warehouse_id=WarehouseIdVO(uuid4())),
            dict(owner_id=StockOwnerIdVO(uuid4())),
        ):
            with self.assertRaises(ShipmentExecutionMismatchError):
                self.build(execution=replace(snapshot, **changes))

    def test_matching_sku_is_not_enough_to_replace_item_or_base_unit(self) -> None:
        """Проверяются идентичность товара и точная базовая единица каждой выбранной строки."""
        snapshot = self.execution.reservation_snapshot()
        for changes in (
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
        ):
            with self.assertRaises(ShipmentExecutionMismatchError):
                self.build(
                    execution=replace(
                        snapshot,
                        lines=(
                            replace(snapshot.lines[0], **changes),
                            *snapshot.lines[1:],
                        ),
                    )
                )

    def test_quantity_limit_is_checked_per_line_and_accumulates_previous_progress(
        self,
    ) -> None:
        """Сумма нескольких фактических строк ограничена остатком каждой строки, а не общей суммой товара."""
        with self.assertRaises(ShipmentQuantityExceededError):
            self.build(
                bindings=tuple(
                    replace(value, shipment_line_id=self.fixture.line_b.id)
                    for value in self.bindings
                )
            )
        partial = self.register()
        with self.assertRaises(ShipmentQuantityExceededError):
            self.build(shipment=partial.execution_snapshot())
        result = self.build()
        first = result.lines[0]
        with self.assertRaises(ShipmentQuantityExceededError):
            self.register(
                replace(
                    result, lines=(replace(first, quantity=QuantityVO(Decimal(100))),)
                )
            )

    def test_only_confirmed_and_partial_states_accept_progress(self) -> None:
        """Черновик, отменённый и полностью отгруженный план не принимают новые факты."""
        full = replace(
            self.shipment,
            status=ShipmentStatus.SHIPPED,
            lines=tuple(
                replace(line, shipped_qty=line.planned_qty)
                for line in self.shipment.lines
            ),
        )
        for shipment in (
            self.fixture.draft(),
            self.fixture.cancel(self.fixture.draft()),
            full,
        ):
            with self.assertRaises(ShipmentStatusError):
                self.build(shipment=shipment.execution_snapshot())
            with self.assertRaises(ShipmentStatusError):
                shipment.register_execution(
                    replace(self.build(), shipment_version=shipment.version),
                    expected_version=shipment.version,
                    updated_at=self.time,
                )

    def test_partial_and_full_states_remain_uneditable_and_uncancellable(self) -> None:
        """Регистрация прогресса не открывает редактирование, повторное подтверждение или отмену плана."""
        partial = self.register()
        full = replace(
            partial,
            status=ShipmentStatus.SHIPPED,
            lines=tuple(
                replace(line, shipped_qty=line.planned_qty) for line in partial.lines
            ),
        )
        for shipment in (partial, full):
            for operation in (
                lambda: shipment.cancel(
                    expected_version=shipment.version, updated_at=self.time
                ),
                lambda: shipment.remove_line(
                    self.fixture.line_a.id,
                    expected_version=shipment.version,
                    updated_at=self.time,
                ),
                lambda: self.fixture.add(shipment, expected_version=shipment.version),
                lambda: self.fixture.change(
                    shipment, expected_version=shipment.version
                ),
                lambda: self.fixture.confirm(
                    shipment, expected_version=shipment.version
                ),
            ):
                with self.assertRaises(ShipmentStatusError):
                    operation()

    def test_expected_version_is_strict_and_checked_before_policy_or_arithmetic(
        self,
    ) -> None:
        """Версия команды проверяется до чужого снимка и потенциально дорогой собственной арифметики."""
        for version in (True, False, -1, "3", Decimal(3), None):
            with self.assertRaises(InvalidShipmentValueError):
                self.register(expected_version=version)
        registration = self.build()
        with patch.object(
            ShipmentExecutionPolicy,
            "ensure_compatible",
            side_effect=RuntimeError("must not run"),
        ):
            with self.assertRaises(ShipmentVersionConflictError):
                self.register(registration, expected_version=2)
            with self.assertRaises(InvalidShipmentValueError):
                replace(self.shipment, version=True).register_execution(
                    registration, expected_version=3, updated_at=self.time
                )

    def test_registration_is_bound_to_shipment_identity_and_current_version(
        self,
    ) -> None:
        """Результат другого плана или старой версии нельзя применить к текущему состоянию."""
        result = self.build()
        with self.assertRaises(ShipmentExecutionMismatchError):
            self.register(replace(result, shipment_id=ShipmentIdVO(uuid4())))
        with self.assertRaises(ShipmentVersionConflictError):
            self.register(replace(result, shipment_version=2))
        partial = self.register(result)
        with self.assertRaises(ShipmentVersionConflictError):
            partial.register_execution(
                result, expected_version=partial.version, updated_at=self.time
            )

    def test_registration_cannot_reassign_reservation_item_unit_or_line(self) -> None:
        """Корень повторно сверяет неизменяемые привязки результата со своими строками."""
        result = self.build()
        line = result.lines[0]
        for changes in (
            dict(reservation_id=StockReservationIdVO(uuid4())),
            dict(inventory_item_id=InventoryItemIdVO(uuid4())),
            dict(base_uom=UomCodeVO("G")),
            dict(shipment_line_id=ShipmentLineIdVO(uuid4())),
        ):
            with self.assertRaises(ShipmentExecutionMismatchError):
                self.register(replace(result, lines=(replace(line, **changes),)))

    def test_fact_and_registration_time_are_explicit_monotonic_and_utc(self) -> None:
        """Факт не раньше состояния плана, регистрация не раньше факта; ввод времени нормализуется в UTC."""
        snapshot = self.execution.reservation_snapshot()
        with self.assertRaises(ShipmentTimeError):
            self.build(
                execution=replace(
                    snapshot, executed_at=self.time - timedelta(seconds=1)
                )
            )
        future = self.build(
            execution=replace(snapshot, executed_at=self.time + timedelta(seconds=1))
        )
        with self.assertRaises(ShipmentTimeError):
            self.register(future)
        for updated in (
            self.time - timedelta(seconds=1),
            self.time.replace(tzinfo=None),
            None,
            "now",
        ):
            with self.assertRaises(ShipmentTimeError):
                self.register(updated_at=updated)
        later = self.time + timedelta(minutes=1)
        result = self.register(
            updated_at=later.astimezone(timezone(timedelta(hours=2)))
        )
        self.assertEqual(result.updated_at, later)
        with self.assertRaises(ShipmentTimeError):
            self.build(shipment=result.execution_snapshot())

    def test_restore_checks_full_status_matrix_without_current_external_context(
        self,
    ) -> None:
        """История проверяется по собственному прогрессу, без актуальных резервов и системного коэффициента."""
        zero = self.shipment.lines
        partial = self.register().lines
        full = tuple(replace(line, shipped_qty=line.planned_qty) for line in zero)
        valid = {
            ShipmentStatus.DRAFT: zero,
            ShipmentStatus.CONFIRMED: zero,
            ShipmentStatus.CANCELLED: zero,
            ShipmentStatus.PARTIALLY_SHIPPED: partial,
            ShipmentStatus.SHIPPED: full,
        }
        for status, lines in valid.items():
            self.assertEqual(
                self.restore(self.shipment, status=status, lines=lines).lines, lines
            )
            for bad in (zero, partial, full):
                if bad != lines:
                    with self.assertRaises(InvalidShipmentValueError):
                        self.restore(self.shipment, status=status, lines=bad)
        for status in (
            ShipmentStatus.CONFIRMED,
            ShipmentStatus.PARTIALLY_SHIPPED,
            ShipmentStatus.SHIPPED,
        ):
            with self.assertRaises(EmptyShipmentError):
                self.restore(self.shipment, status=status, lines=())
        historical = replace(
            partial[0],
            planned_qty=QuantityVO(Decimal(6)),
            conversion=replace(
                partial[0].conversion,
                quantity=QuantityVO(Decimal(3)),
                factor_to_base=Decimal(2),
            ),
        )
        self.assertEqual(
            self.restore(
                self.shipment,
                status=ShipmentStatus.PARTIALLY_SHIPPED,
                lines=(historical,),
            ).lines[0],
            historical,
        )

    def test_plan_snapshot_is_revalidated_at_policy_boundary(self) -> None:
        """Поддельные типы, версии, UTC, дубли и несовместимые состояния снимка отклоняются потребителем."""
        snapshot = self.shipment.execution_snapshot()
        for changes in (
            dict(id=uuid4()),
            dict(version=True),
            dict(version=-1),
            dict(status="CONFIRMED"),
            dict(warehouse_id=uuid4()),
            dict(owner_id=None),
            dict(updated_at=self.time.replace(tzinfo=None)),
            dict(lines=[]),
            dict(lines=(None,)),
            dict(lines=(snapshot.lines[0], snapshot.lines[0])),
            dict(lines=()),
            dict(status=ShipmentStatus.SHIPPED),
            dict(status=ShipmentStatus.PARTIALLY_SHIPPED),
        ):
            with self.assertRaises(InvalidShipmentExecutionPlanSnapshotError):
                self.build(shipment=replace(snapshot, **changes))
        row = snapshot.lines[0]
        for changes in (
            dict(id=uuid4()),
            dict(inventory_item_id=None),
            dict(base_uom=None),
            dict(reservation_id=None),
            dict(planned_qty=QuantityVO(Decimal(0))),
            dict(shipped_qty=None),
            dict(shipped_qty=QuantityVO(Decimal(4))),
        ):
            with self.assertRaises(InvalidShipmentExecutionPlanSnapshotError):
                self.build(shipment=replace(snapshot, lines=(replace(row, **changes),)))

    def test_registration_snapshot_revalidates_types_counts_scope_and_actual_ids(
        self,
    ) -> None:
        """Результат не допускает пустые/повторные строки и произвольные типы даже при прямом конструкторе."""
        result = self.build()
        for changes in (
            dict(shipment_id=uuid4()),
            dict(shipment_version=True),
            dict(shipment_version=-1),
            dict(execution_id=uuid4()),
            dict(operation_type="ISSUE"),
            dict(operation_type=StockOperationType.RECEIPT),
            dict(warehouse_id=None),
            dict(owner_id=None),
            dict(executed_at=self.time.replace(tzinfo=None)),
            dict(lines=[]),
            dict(lines=()),
            dict(lines=(None,)),
            dict(lines=(result.lines[0], result.lines[0])),
        ):
            bad = replace(result, **changes)
            with self.assertRaises(InvalidShipmentExecutionRegistrationSnapshotError):
                self.register(bad)
            with self.assertRaises(InvalidShipmentExecutionRegistrationSnapshotError):
                bad.reservation_bindings()
        row = result.lines[0]
        for changes in (
            dict(shipment_line_id=uuid4()),
            dict(inventory_item_id=None),
            dict(base_uom=None),
            dict(reservation_id=None),
            dict(quantity=QuantityVO(Decimal(0))),
            dict(quantity=Decimal(1)),
            dict(execution_line_ids=[]),
            dict(execution_line_ids=()),
            dict(execution_line_ids=(uuid4(),)),
            dict(execution_line_ids=(row.execution_line_ids[0],) * 2),
        ):
            with self.assertRaises(InvalidShipmentExecutionRegistrationSnapshotError):
                self.register(replace(result, lines=(replace(row, **changes),)))
        first, second = result.lines
        for changes in (
            dict(reservation_id=first.reservation_id),
            dict(execution_line_ids=first.execution_line_ids),
        ):
            with self.assertRaises(InvalidShipmentExecutionRegistrationSnapshotError):
                self.register(
                    replace(result, lines=(first, replace(second, **changes)))
                )
        with self.assertRaises(FrozenInstanceError):
            result.shipment_version = 9

    def test_wrong_purpose_and_full_aggregates_cannot_replace_snapshots(self) -> None:
        """Контракты назначения не принимают корни и снимки другого назначения."""
        for shipment in (None, self.shipment, self.fixture.a.shipment_snapshot()):
            with self.assertRaises(InvalidShipmentExecutionPlanSnapshotError):
                self.build(shipment=shipment)
        for execution in (None, self.execution, self.shipment.execution_snapshot()):
            with self.assertRaises(InvalidStockExecutionReservationSnapshotError):
                self.build(execution=execution)
        with self.assertRaises(InvalidShipmentExecutionRegistrationSnapshotError):
            self.register(self.execution.reservation_snapshot())

    def test_grams_are_already_converted_in_fact_and_not_reinterpreted_by_shipment(
        self,
    ) -> None:
        """Исполнение 1000 G даёт ровно 1 KG; плановый ввод и коэффициент Shipment не меняются."""
        execution = self.fact(("1000",), uom="G")
        registration = self.build(
            execution=execution.reservation_snapshot(),
            bindings=(
                ShipmentExecutionBindingVO(
                    execution.lines[0].id, self.fixture.line_a.id
                ),
            ),
        )
        after = self.register(registration)
        self.assertEqual(after.lines[0].shipped_qty.value, Decimal(1))
        self.assertEqual(after.lines[0].conversion, self.fixture.line_a.conversion)
        self.assertEqual(execution.lines[0].conversion.uom, UomCodeVO("G"))

    def test_exact_arithmetic_is_independent_of_hostile_decimal_context(self) -> None:
        """Суммирование и остаток не округляются внешним контекстом Decimal."""
        execution = self.fact(("1.05", "1.10"))
        bindings = tuple(
            ShipmentExecutionBindingVO(line.id, self.fixture.line_a.id)
            for line in execution.lines
        )
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            result = self.build(
                execution=execution.reservation_snapshot(), bindings=bindings
            )
            after = self.register(result)
            self.assertEqual(after.lines[0].shipped_qty.value, Decimal("2.15"))
            self.assertEqual(after.lines[0].remaining_qty().value, Decimal("0.85"))

    def test_unrepresentable_group_sum_has_controlled_domain_error(self) -> None:
        """Защитный предел общей арифметики сохраняется при группировке фактических строк."""
        snapshot = self.execution.reservation_snapshot()
        large = replace(snapshot.lines[0], quantity=QuantityVO(Decimal("1E+1000001")))
        plan = self.shipment.execution_snapshot()
        huge_plan = replace(
            plan,
            lines=(replace(plan.lines[0], planned_qty=large.quantity), *plan.lines[1:]),
        )
        with self.assertRaises(StockQuantityArithmeticError):
            self.build(
                shipment=huge_plan,
                execution=replace(snapshot, lines=(large, *snapshot.lines[1:])),
            )

    def test_end_to_end_progress_reservations_and_pool_share_selected_fact_quantities(
        self,
    ) -> None:
        """Из одних назначений получаются 2+1 KG прогресса, погашения A/B и один переход общего пула."""
        f = self.fixture
        registration = self.build()
        progress = self.register(registration)
        consumptions = StockExecutionReservationPolicy.build_consumptions(
            execution=self.execution.reservation_snapshot(),
            bindings=registration.reservation_bindings(),
            reservations=(f.a.execution_snapshot(), f.b.execution_snapshot()),
        )
        by_id = {value.reservation_id: value for value in consumptions}
        a = f.a.consume_execution(
            by_id[f.a.id],
            expected_version=f.a.version,
            inventory_item=f.item.stock_snapshot(),
            updated_at=self.time,
        )
        b = f.b.consume_execution(
            by_id[f.b.id],
            expected_version=f.b.version,
            inventory_item=f.item.stock_snapshot(),
            updated_at=self.time,
        )
        position = self.position.apply_delta(
            StockDeltaVO(Decimal(-3)),
            inventory_item=f.item.stock_snapshot(),
            location=self.location,
            warehouse=f.warehouse,
        )
        pool = f.pool.consume_reservations(
            consumptions,
            expected_version=f.pool.version,
            inventory_item=f.item.availability_snapshot(),
            warehouse=f.warehouse,
            as_of=self.time.date(),
            positions=(position.availability_snapshot(),),
            locations=(self.location,),
        )
        self.assertEqual(
            tuple(line.shipped_qty.value for line in progress.lines),
            (Decimal(2), Decimal(1)),
        )
        self.assertEqual(
            (
                a.reserved_qty.value,
                a.consumed_qty.value,
                b.reserved_qty.value,
                b.consumed_qty.value,
            ),
            (Decimal(2), Decimal(2), Decimal(2), Decimal(1)),
        )
        self.assertEqual(
            (pool.eligible_qty.value, pool.reserved_qty.value, pool.version),
            (Decimal(7), Decimal(4), 2),
        )
        self.assertEqual(
            (f.a.reserved_qty.value, f.b.reserved_qty.value, f.pool.reserved_qty.value),
            (Decimal(4), Decimal(3), Decimal(7)),
        )

    def test_reservation_limits_and_expiration_stay_owned_by_reservation(self) -> None:
        """Прогресс-кандидат не подменяет проверку текущего удержания и фактического времени резервом."""
        f = self.fixture
        consumptions = StockExecutionReservationPolicy.build_consumptions(
            execution=self.execution.reservation_snapshot(),
            bindings=self.build().reservation_bindings(),
            reservations=(f.a.execution_snapshot(), f.b.execution_snapshot()),
        )
        a_consumption = next(
            value for value in consumptions if value.reservation_id == f.a.id
        )
        with self.assertRaises(StockReservationConsumptionExceededError):
            replace(
                f.a,
                reserved_qty=QuantityVO(Decimal(1)),
                status=StockReservationStatus.PARTIALLY_RESERVED,
            ).consume_execution(
                a_consumption,
                expected_version=f.a.version,
                inventory_item=f.item.stock_snapshot(),
                updated_at=self.time,
            )
        with self.assertRaises(StockReservationExpiredError):
            replace(f.a, expires_at=self.time).consume_execution(
                a_consumption,
                expected_version=f.a.version,
                inventory_item=f.item.stock_snapshot(),
                updated_at=self.time,
            )
        self.assertEqual(self.register().status, ShipmentStatus.PARTIALLY_SHIPPED)
        self.assertEqual(f.a.reserved_qty.value, Decimal(4))
        later = self.time + timedelta(hours=2)
        after = f.a.consume_execution(
            a_consumption,
            expected_version=f.a.version,
            inventory_item=f.item.stock_snapshot(),
            updated_at=later,
        )
        self.assertEqual(after.consumed_qty.value, Decimal(2))

    def test_registration_does_not_claim_global_deduplication(self) -> None:
        """Подготовленный результат устаревает, но повторная сборка факта по новой версии требует внешней дедупликации."""
        partial = self.register(self.build(bindings=self.bindings[:1]))
        again = self.build(
            shipment=partial.execution_snapshot(), bindings=self.bindings[:1]
        )
        twice = partial.register_execution(
            again, expected_version=partial.version, updated_at=self.time
        )
        self.assertEqual(twice.lines[0].shipped_qty.value, Decimal(2))
        other = replace(self.shipment, id=ShipmentIdVO(uuid4()))
        self.assertEqual(
            self.build(shipment=other.execution_snapshot()).shipment_id, other.id
        )

    def test_complete_shipment_consumes_only_its_plan_and_leaves_excess_holds(
        self,
    ) -> None:
        """Полная отгрузка 3+2 KG погашает ровно 5 из 7 удержанных KG без автоматического освобождения остатка."""
        f = self.fixture
        execution = self.fact(("3", "2"))
        registration = self.build(
            execution=execution.reservation_snapshot(),
            bindings=tuple(
                ShipmentExecutionBindingVO(fact.id, plan.id)
                for fact, plan in zip(execution.lines, self.shipment.lines)
            ),
        )
        full = self.register(registration)
        consumptions = StockExecutionReservationPolicy.build_consumptions(
            execution=execution.reservation_snapshot(),
            bindings=registration.reservation_bindings(),
            reservations=(f.a.execution_snapshot(), f.b.execution_snapshot()),
        )
        by_id = {value.reservation_id: value for value in consumptions}
        a = f.a.consume_execution(
            by_id[f.a.id],
            expected_version=f.a.version,
            inventory_item=f.item.stock_snapshot(),
            updated_at=self.time,
        )
        b = f.b.consume_execution(
            by_id[f.b.id],
            expected_version=f.b.version,
            inventory_item=f.item.stock_snapshot(),
            updated_at=self.time,
        )
        self.assertEqual(full.status, ShipmentStatus.SHIPPED)
        self.assertEqual(
            (a.reserved_qty.value, b.reserved_qty.value), (Decimal(1), Decimal(1))
        )
        self.assertEqual(
            (a.consumed_qty.value, b.consumed_qty.value), (Decimal(3), Decimal(2))
        )

    def test_serial_tracking_progress_aggregates_individual_instances_into_whole_pcs(
        self,
    ) -> None:
        """Пять индивидуальных серийных фактов по 1 PCS исполняют строки плана 3+2 PCS."""
        f = self.fixture
        for mode in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL):
            item = replace(
                f.item,
                base_uom=UomCodeVO("PCS"),
                quantity_rules=QuantityRulesVO(Decimal(1)),
                tracking_mode=mode,
            )
            lines = tuple(
                ShipmentLine.create(
                    identifier=old.id,
                    inventory_item=item.stock_snapshot(),
                    reservation=replace(
                        reservation, base_uom=item.base_uom
                    ).shipment_snapshot(),
                    quantity=old.planned_qty,
                    uom=item.base_uom,
                )
                for old, reservation in zip(self.shipment.lines, (f.a, f.b))
            )
            shipment = replace(self.shipment, lines=lines)
            lot_id = (
                StockLotIdVO(uuid4()) if mode is TrackingMode.LOT_AND_SERIAL else None
            )
            actual = tuple(
                StockExecutionLine.create(
                    identifier=StockExecutionLineIdVO(uuid4()),
                    document_line_id=StockDocumentLineIdVO(uuid4()),
                    inventory_item=item.execution_snapshot(),
                    quantity=QuantityVO(Decimal(1)),
                    uom=item.base_uom,
                    route=IssueExecutionRouteVO(
                        replace(
                            self.position.dimensions,
                            lot_id=lot_id,
                            serial_id=StockSerialIdVO(uuid4()),
                        )
                    ),
                )
                for _ in range(5)
            )
            execution = replace(self.execution, lines=actual)
            registration = self.build(
                shipment=shipment.execution_snapshot(),
                execution=execution.reservation_snapshot(),
                bindings=tuple(
                    ShipmentExecutionBindingVO(line.id, lines[0 if index < 3 else 1].id)
                    for index, line in enumerate(actual)
                ),
            )
            full = shipment.register_execution(
                registration, expected_version=3, updated_at=self.time
            )
            self.assertEqual(full.status, ShipmentStatus.SHIPPED)
            self.assertEqual(
                tuple(line.shipped_qty.value for line in full.lines),
                (Decimal(3), Decimal(2)),
            )

    def test_failures_leave_all_sources_unchanged(self) -> None:
        """Неудачная регистрация не меняет ни подтверждённый план, ни исполнение, ни резервы."""
        before = (
            self.shipment,
            self.execution,
            self.fixture.a,
            self.fixture.b,
            self.fixture.pool,
        )
        result = self.build()
        with self.assertRaises(ShipmentTimeError):
            self.register(replace(result, executed_at=self.time + timedelta(days=1)))
        self.assertEqual(
            (
                self.shipment,
                self.execution,
                self.fixture.a,
                self.fixture.b,
                self.fixture.pool,
            ),
            before,
        )


if __name__ == "__main__":
    unittest.main()
