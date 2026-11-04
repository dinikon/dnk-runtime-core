"""Явное назначение фактических строк расхода резервам и применение сгруппированных погашений."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, Inexact, Rounded, localcontext
from itertools import permutations
from uuid import uuid4

from src.modules.inventory.domain.availability_pool.aggregate import AvailabilityPool
from src.modules.inventory.domain.availability_pool.error import (
    AvailabilityPoolConsumptionMismatchError,
    AvailabilityPoolUomMismatchError,
    AvailabilityPoolVersionConflictError,
    ExcessiveReservationConsumptionError,
    InvalidAvailabilityPoolValueError,
    InvalidPoolReservationConsumptionsError,
)
from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.error import (
    QuantityConversionMismatchError,
    QuantityStepError,
    StockQuantityArithmeticError,
    UnknownUomError,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.stock_execution_reservation import (
    StockExecutionReservationPolicy,
)
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
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
from src.modules.inventory.domain.stock_reservation.aggregate import StockReservation
from src.modules.inventory.domain.stock_reservation.error import (
    InvalidReservationConsumptionContextError,
    InvalidReservationExecutionBindingError,
    InvalidStockReservationConsumptionSnapshotError,
    InvalidStockReservationExecutionSnapshotError,
    InvalidStockReservationValueError,
    StockReservationConsumptionExceededError,
    StockReservationConsumptionMismatchError,
    StockReservationExpiredError,
    StockReservationStatusError,
    StockReservationTimeError,
    StockReservationUomMismatchError,
    StockReservationVersionConflictError,
)
from src.modules.inventory.domain.stock_reservation.value_object.execution_binding import (
    ReservationExecutionBindingVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.identifier import (
    StockReservationIdVO,
)
from src.modules.inventory.domain.stock_reservation.value_object.source import (
    ReservationSourceVO,
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
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class ExecutionReservationDomainTests(unittest.TestCase):
    """Проверяет соответствия строк, минимальные снимки, группировку и границы применения."""

    def setUp(self) -> None:
        """Готовит расход 2+3+1+4 KG и два удержания одного товара в общем пуле."""
        self.time = datetime(2026, 11, 4, 10, tzinfo=UTC)
        self.created = self.time - timedelta(hours=1)
        self.warehouse = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.location = StockLocationSnapshot(
            StockLocationIdVO(uuid4()), self.warehouse.id, LocationType.STORAGE, True
        )
        self.owner = StockOwnerIdVO(uuid4())
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("ITEM"),
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.05")),
        )
        self.position = StockPosition.restore(
            identifier=StockPositionIdVO(uuid4()),
            dimensions=StockDimensionsVO(
                self.item.id,
                self.location.id,
                self.owner,
                None,
                None,
                StockStatus.SELLABLE,
            ),
            base_uom=self.item.base_uom,
            on_hand_qty=QuantityVO(Decimal(20)),
            version=7,
        )
        pool = AvailabilityPool.create(
            identifier=AvailabilityPoolIdVO(uuid4()),
            key=AvailabilityPoolKeyVO(self.item.id, self.warehouse.id, self.owner),
            **self.context(),
        )
        self.a = self.reservation(pool, "8", "ORDER/A")
        self.b = self.reservation(pool, "4", "ORDER/B")
        self.pool = pool.reserve(
            QuantityVO(Decimal(12)), expected_version=0, **self.context()
        )
        self.lines = tuple(self.line(amount) for amount in ("2", "3", "1", "4"))
        self.execution = StockExecution.restore(
            identifier=StockExecutionIdVO(uuid4()),
            document_id=StockDocumentIdVO(uuid4()),
            document_version=0,
            operation_type=StockOperationType.ISSUE,
            warehouse_id=self.warehouse.id,
            owner_id=self.owner,
            executed_at=self.time,
            lines=self.lines,
        )
        self.bindings = (
            ReservationExecutionBindingVO(self.lines[0].id, self.a.id),
            ReservationExecutionBindingVO(self.lines[1].id, self.a.id),
            ReservationExecutionBindingVO(self.lines[2].id, self.b.id),
        )

    def context(self) -> dict[str, object]:
        """Возвращает физические снимки для оценки одного пула."""
        return dict(
            inventory_item=self.item.availability_snapshot(),
            warehouse=self.warehouse,
            as_of=self.time.date(),
            positions=(self.position.availability_snapshot(),),
            locations=(self.location,),
        )

    def reservation(
        self, pool: AvailabilityPool, amount: str, reference: str
    ) -> StockReservation:
        """Готовит удержание с отдельным основанием и явной версией, не изменяя переданный пул."""
        reservation = StockReservation.create(
            identifier=StockReservationIdVO(uuid4()),
            pool=pool.reservation_snapshot(),
            inventory_item=self.item.stock_snapshot(),
            source_ref=ReservationSourceVO("order_line", reference),
            requested_qty=QuantityVO(Decimal(amount)),
            created_at=self.created,
            expires_at=self.time + timedelta(hours=1),
        )
        return reservation.add_reserved(
            QuantityVO(Decimal(amount)),
            expected_version=0,
            inventory_item=self.item.stock_snapshot(),
            updated_at=self.created,
        )

    def line(self, amount: str) -> StockExecutionLine:
        """Создаёт положительную фактическую строку в базовой единице с полным маршрутом."""
        return StockExecutionLine.create(
            identifier=StockExecutionLineIdVO(uuid4()),
            document_line_id=StockDocumentLineIdVO(uuid4()),
            inventory_item=self.item.execution_snapshot(),
            quantity=QuantityVO(Decimal(amount)),
            uom=self.item.base_uom,
            route=IssueExecutionRouteVO(self.position.dimensions),
        )

    def build(self, **changes: object) -> tuple:
        """Строит результаты по фактическим строкам без изменения их источников."""
        return StockExecutionReservationPolicy.build_consumptions(
            **(
                dict(
                    execution=self.execution.reservation_snapshot(),
                    bindings=self.bindings,
                    reservations=(
                        self.a.execution_snapshot(),
                        self.b.execution_snapshot(),
                    ),
                )
                | changes
            )
        )

    def apply(
        self, reservation: StockReservation, consumption: object, **changes: object
    ) -> StockReservation:
        """Применяет одно сгруппированное погашение к текущей версии обязательства."""
        return reservation.consume_execution(
            consumption,
            **(
                dict(
                    expected_version=reservation.version,
                    inventory_item=self.item.stock_snapshot(),
                    updated_at=self.time,
                )
                | changes
            ),
        )

    def apply_pool(self, consumptions: object, **changes: object) -> AvailabilityPool:
        """Применяет набор к общему пулу по ожидаемой версии и снимкам после расхода."""
        after = self.position.apply_delta(
            StockDeltaVO(Decimal(-10)),
            inventory_item=self.item.stock_snapshot(),
            location=self.location,
            warehouse=self.warehouse,
        )
        return self.pool.consume_reservations(
            consumptions,
            **(
                dict(expected_version=self.pool.version)
                | self.context()
                | dict(positions=(after.availability_snapshot(),))
                | changes
            ),
        )

    def test_binding_is_typed_and_immutable(self) -> None:
        """Соответствие содержит только два типизированных ID без произвольной части количества."""
        binding = self.bindings[0]
        for changes in (
            dict(execution_line_id=uuid4()),
            dict(reservation_id=self.pool.id),
        ):
            with self.assertRaises(InvalidReservationExecutionBindingError):
                replace(binding, **changes)
        with self.assertRaises(FrozenInstanceError):
            binding.reservation_id = self.b.id

    def test_snapshot_getters_are_minimal_frozen_and_check_originals(self) -> None:
        """Геттеры не раскрывают маршруты, Entity или счётчики и проверяют полные исходные агрегаты."""
        execution = self.execution.reservation_snapshot()
        reservation = self.a.execution_snapshot()
        self.assertEqual(
            set(execution.lines[0].__dataclass_fields__),
            {"id", "inventory_item_id", "base_uom", "quantity"},
        )
        self.assertEqual(
            set(reservation.__dataclass_fields__),
            {"id", "pool_id", "key", "base_uom", "version"},
        )
        execution.ensure_valid()
        reservation.ensure_valid()
        with self.assertRaises(FrozenInstanceError):
            reservation.version = 2
        with self.assertRaises(FrozenInstanceError):
            execution.lines[0].quantity = QuantityVO(Decimal(10))
        with self.assertRaises(InvalidStockReservationValueError):
            replace(self.a, version=True).execution_snapshot()
        malformed = replace(self.lines[0], quantity=QuantityVO(Decimal(10)))
        with self.assertRaises(QuantityConversionMismatchError):
            replace(self.execution, lines=(malformed,)).reservation_snapshot()

    def test_groups_whole_lines_by_explicit_reservation_and_excludes_unbound_line(
        self,
    ) -> None:
        """Два одинаковых товара не смешиваются: A получает 5, B — 1, непривязанные 4 не погашаются."""
        result = self.build()
        by_id = {value.reservation_id: value for value in result}
        self.assertEqual(
            (by_id[self.a.id].quantity.value, by_id[self.b.id].quantity.value),
            (Decimal(5), Decimal(1)),
        )
        self.assertEqual(
            set(by_id[self.a.id].execution_line_ids),
            {self.lines[0].id, self.lines[1].id},
        )
        self.assertEqual(by_id[self.b.id].execution_line_ids, (self.lines[2].id,))
        self.assertNotIn(
            self.lines[3].id,
            {identifier for value in result for identifier in value.execution_line_ids},
        )
        for value in result:
            self.assertEqual(
                (
                    value.execution_id,
                    value.consumed_at,
                    value.pool_id,
                    value.key,
                    value.base_uom,
                    value.reservation_version,
                ),
                (
                    self.execution.id,
                    self.time,
                    self.pool.id,
                    self.pool.key,
                    self.item.base_uom,
                    1,
                ),
            )
            value.ensure_valid()
        self.assertEqual(
            (
                self.a.reserved_qty.value,
                self.b.reserved_qty.value,
                self.pool.reserved_qty.value,
            ),
            (Decimal(8), Decimal(4), Decimal(12)),
        )

    def test_result_is_deterministic_for_all_input_orders(self) -> None:
        """Порядок строк, соответствий и снимков не меняет суммы, порядок результатов и ID строк."""
        expected = self.build()
        for bindings in permutations(self.bindings):
            for reservations in permutations(
                (self.a.execution_snapshot(), self.b.execution_snapshot())
            ):
                execution = replace(
                    self.execution.reservation_snapshot(),
                    lines=tuple(reversed(self.execution.reservation_snapshot().lines)),
                )
                self.assertEqual(
                    self.build(
                        execution=execution,
                        bindings=bindings,
                        reservations=reservations,
                    ),
                    expected,
                )
        self.assertEqual(
            [value.reservation_id for value in expected],
            sorted((self.a.id, self.b.id), key=lambda value: value.uuid.int),
        )

    def test_empty_assignment_is_valid_only_with_empty_reservation_context(
        self,
    ) -> None:
        """Расход без резервов возвращает пустой результат без фиктивного погашения."""
        self.assertEqual(self.build(bindings=(), reservations=()), ())
        with self.assertRaises(InvalidReservationConsumptionContextError):
            self.build(bindings=())
        with self.assertRaises(InvalidPoolReservationConsumptionsError):
            self.apply_pool(())

    def test_only_issue_is_allowed_even_for_empty_assignments(self) -> None:
        """Приход и внутреннее перемещение не становятся погашением резерва."""
        for kind in (StockOperationType.RECEIPT, StockOperationType.INTERNAL_MOVE):
            with self.assertRaises(InvalidReservationConsumptionContextError):
                self.build(
                    execution=replace(
                        self.execution.reservation_snapshot(), operation_type=kind
                    ),
                    bindings=(),
                    reservations=(),
                )

    def test_duplicate_assignment_unknown_line_or_reservation_is_rejected(self) -> None:
        """Строка не назначается дважды даже тому же резерву; неизвестные ID не игнорируются."""
        for extra in (
            self.bindings[0],
            ReservationExecutionBindingVO(self.lines[0].id, self.b.id),
            ReservationExecutionBindingVO(StockExecutionLineIdVO(uuid4()), self.a.id),
            ReservationExecutionBindingVO(
                self.lines[3].id, StockReservationIdVO(uuid4())
            ),
        ):
            with self.assertRaises(InvalidReservationConsumptionContextError):
                self.build(bindings=(*self.bindings, extra))

    def test_exact_unique_reservation_context_is_required(self) -> None:
        """Лишние, отсутствующие и повторные снимки резервов отклоняются."""
        for values in (
            (),
            (self.a.execution_snapshot(),),
            (
                self.a.execution_snapshot(),
                self.b.execution_snapshot(),
                self.a.execution_snapshot(),
            ),
            (
                self.a.execution_snapshot(),
                self.b.execution_snapshot(),
                replace(self.a.execution_snapshot(), id=StockReservationIdVO(uuid4())),
            ),
        ):
            with self.assertRaises(InvalidReservationConsumptionContextError):
                self.build(reservations=values)

    def test_item_warehouse_owner_and_unit_must_match_selected_line(self) -> None:
        """Совпадение SKU не заменяет полную область учёта и базовую единицу."""
        for change in (
            dict(
                key=replace(self.pool.key, inventory_item_id=InventoryItemIdVO(uuid4()))
            ),
            dict(key=replace(self.pool.key, warehouse_id=WarehouseIdVO(uuid4()))),
            dict(key=replace(self.pool.key, owner_id=StockOwnerIdVO(uuid4()))),
            dict(base_uom=UomCodeVO("G")),
        ):
            with self.assertRaises(InvalidReservationConsumptionContextError):
                self.build(
                    reservations=tuple(
                        replace(value.execution_snapshot(), **change)
                        for value in (self.a, self.b)
                    )
                )
        with self.assertRaises(InvalidReservationConsumptionContextError):
            self.build(
                reservations=(
                    self.a.execution_snapshot(),
                    replace(self.b.execution_snapshot(), base_uom=UomCodeVO("G")),
                )
            )

    def test_policy_rejects_entities_and_non_tuple_inputs(self) -> None:
        """Полные агрегаты, старые снимки и произвольные коллекции не подменяют контракт."""
        with self.assertRaises(InvalidStockExecutionReservationSnapshotError):
            self.build(execution=self.execution)
        for changes in (dict(bindings=[]), dict(reservations=[])):
            with self.assertRaises(InvalidReservationConsumptionContextError):
                self.build(**changes)
        with self.assertRaises(InvalidReservationExecutionBindingError):
            self.build(bindings=(self.lines[0],))
        with self.assertRaises(InvalidStockReservationExecutionSnapshotError):
            self.build(reservations=(self.a, self.b))

    def test_execution_snapshot_revalidates_types_positive_lines_and_utc_time(
        self,
    ) -> None:
        """Ручное создание снимка не обходит собственные типы, уникальность строк и время."""
        snapshot = self.execution.reservation_snapshot()
        for changes in (
            dict(id=uuid4()),
            dict(operation_type="ISSUE"),
            dict(warehouse_id=uuid4()),
            dict(owner_id=uuid4()),
            dict(executed_at=self.time.replace(tzinfo=None)),
            dict(lines=()),
            dict(lines=[]),
            dict(lines=(snapshot.lines[0], snapshot.lines[0])),
            dict(lines=(self.lines[0],)),
        ):
            with self.assertRaises(InvalidStockExecutionReservationSnapshotError):
                self.build(execution=replace(snapshot, **changes))
        for changes in (
            dict(id=uuid4()),
            dict(inventory_item_id=uuid4()),
            dict(base_uom="KG"),
            dict(quantity=Decimal(2)),
            dict(quantity=QuantityVO(Decimal(0))),
        ):
            with self.assertRaises(InvalidStockExecutionReservationSnapshotError):
                self.build(
                    execution=replace(
                        snapshot, lines=(replace(snapshot.lines[0], **changes),)
                    )
                )

    def test_reservation_snapshot_revalidates_identity_scope_and_version(self) -> None:
        """Нетипизированные поля и bool-версия не превращаются в разрешённое соответствие."""
        for changes in (
            dict(id=uuid4()),
            dict(pool_id=uuid4()),
            dict(key={}),
            dict(base_uom="KG"),
            dict(version=True),
            dict(version=-1),
        ):
            with self.assertRaises(InvalidStockReservationExecutionSnapshotError):
                self.build(
                    reservations=(
                        replace(self.a.execution_snapshot(), **changes),
                        self.b.execution_snapshot(),
                    )
                )

    def test_reservation_applies_group_once_and_preserves_original(self) -> None:
        """Две строки A суммируются в одно изменение версии и накопленного использования."""
        a_result = next(
            value for value in self.build() if value.reservation_id == self.a.id
        )
        changed = self.apply(self.a, a_result)
        self.assertEqual(
            (
                changed.reserved_qty.value,
                changed.consumed_qty.value,
                changed.version,
                changed.status,
            ),
            (Decimal(3), Decimal(5), 2, StockReservationStatus.PARTIALLY_CONSUMED),
        )
        self.assertEqual(
            (self.a.reserved_qty.value, self.a.consumed_qty.value, self.a.version),
            (Decimal(8), Decimal(0), 1),
        )
        self.assertEqual(a_result.execution_id, self.execution.id)

    def test_reservation_rejects_foreign_target_pool_key_unit_and_versions(
        self,
    ) -> None:
        """Идентичность резерва, область, пул и версия проверяются независимо от общего товара."""
        consumption = next(
            value for value in self.build() if value.reservation_id == self.a.id
        )
        for changes in (
            dict(reservation_id=self.b.id),
            dict(pool_id=AvailabilityPoolIdVO(uuid4())),
            dict(key=replace(self.a.key, owner_id=StockOwnerIdVO(uuid4()))),
        ):
            with self.assertRaises(StockReservationConsumptionMismatchError):
                self.apply(self.a, replace(consumption, **changes))
        with self.assertRaises(StockReservationUomMismatchError):
            self.apply(self.a, replace(consumption, base_uom=UomCodeVO("G")))
        with self.assertRaises(StockReservationVersionConflictError):
            self.apply(self.a, replace(consumption, reservation_version=0))
        changed = self.apply(self.a, consumption)
        with self.assertRaises(StockReservationVersionConflictError):
            self.apply(changed, consumption)

    def test_reservation_keeps_own_limits_status_step_and_deadline_checks(self) -> None:
        """Снимок назначения не заменяет собственные количественные и временные инварианты корня."""
        consumption = next(
            value for value in self.build() if value.reservation_id == self.a.id
        )
        partial = replace(
            self.a,
            reserved_qty=QuantityVO(Decimal(1)),
            status=StockReservationStatus.PARTIALLY_RESERVED,
        )
        with self.assertRaises(StockReservationConsumptionExceededError):
            self.apply(partial, consumption)
        with self.assertRaises(StockReservationExpiredError):
            self.apply(
                self.a,
                replace(consumption, consumed_at=self.a.expires_at),
                updated_at=self.a.expires_at,
            )
        with self.assertRaises(StockReservationTimeError):
            self.apply(self.a, consumption, updated_at=self.time - timedelta(seconds=1))
        with self.assertRaises(StockReservationStatusError):
            self.apply(
                self.a.release_all(expected_version=1, updated_at=self.time),
                consumption,
            )
        with self.assertRaises(QuantityStepError):
            self.apply(
                self.a, replace(consumption, quantity=QuantityVO(Decimal("0.03")))
            )
        with self.assertRaises(InvalidInventoryItemStockSnapshotError):
            self.apply(self.a, consumption, inventory_item=self.item)

    def test_consumption_snapshot_checks_types_unique_lines_positive_quantity_and_time(
        self,
    ) -> None:
        """Повторная проверка не принимает сырые значения и нулевые снимки погашения."""
        consumption = self.build()[0]
        reservation = self.a if consumption.reservation_id == self.a.id else self.b
        for changes in (
            dict(execution_id=uuid4()),
            dict(reservation_id=uuid4()),
            dict(reservation_version=True),
            dict(reservation_version=-1),
            dict(pool_id=uuid4()),
            dict(key={}),
            dict(base_uom="KG"),
            dict(quantity=Decimal(1)),
            dict(quantity=QuantityVO(Decimal("-0.000"))),
            dict(consumed_at=self.time.replace(tzinfo=None)),
            dict(execution_line_ids=[]),
            dict(execution_line_ids=()),
            dict(execution_line_ids=(uuid4(),)),
            dict(execution_line_ids=(self.lines[0].id, self.lines[0].id)),
        ):
            with self.assertRaises(InvalidStockReservationConsumptionSnapshotError):
                self.apply(reservation, replace(consumption, **changes))
        with self.assertRaises(UnknownUomError):
            self.apply(reservation, replace(consumption, base_uom=UomCodeVO("BOX")))
        for value in (None, self.execution, QuantityVO(Decimal(1)), {}):
            with self.assertRaises(InvalidStockReservationConsumptionSnapshotError):
                self.apply(reservation, value)

    def test_pool_groups_two_reservations_once_after_full_physical_issue(self) -> None:
        """Погашение 6 при расходе 10 даёт пул 10/6/4, не вычитая непривязанные строки из резерва."""
        result = self.build()
        for consumptions in permutations(result):
            changed = self.apply_pool(consumptions)
            self.assertEqual(
                (
                    changed.eligible_qty.value,
                    changed.reserved_qty.value,
                    changed.available_qty.value,
                    changed.version,
                ),
                (Decimal(10), Decimal(6), Decimal(4), 2),
            )
        self.assertEqual(
            (
                self.pool.reserved_qty.value,
                self.position.on_hand_qty.value,
                self.position.version,
            ),
            (Decimal(12), Decimal(20), 7),
        )

    def test_pool_rejects_duplicate_reservation_or_line_and_mixed_execution_or_time(
        self,
    ) -> None:
        """Набор переиспользовать строку или смешивать разные факты не может."""
        a, b = sorted(
            self.build(), key=lambda value: value.quantity.value, reverse=True
        )
        for consumptions in (
            (a, a),
            (a, replace(b, reservation_id=a.reservation_id)),
            (a, replace(b, execution_line_ids=(a.execution_line_ids[0],))),
            (a, replace(b, execution_id=StockExecutionIdVO(uuid4()))),
            (a, replace(b, consumed_at=self.time + timedelta(minutes=1))),
        ):
            with self.assertRaises(InvalidPoolReservationConsumptionsError):
                self.apply_pool(consumptions)

    def test_pool_rejects_wrong_target_and_invalid_collections(self) -> None:
        """Каждое погашение проверяется по ID пула, полному ключу и базовой единице."""
        consumption = self.build()[0]
        for changes in (
            dict(pool_id=AvailabilityPoolIdVO(uuid4())),
            dict(
                key=replace(self.pool.key, inventory_item_id=InventoryItemIdVO(uuid4()))
            ),
        ):
            with self.assertRaises(AvailabilityPoolConsumptionMismatchError):
                self.apply_pool((replace(consumption, **changes),))
        with self.assertRaises(AvailabilityPoolUomMismatchError):
            self.apply_pool((replace(consumption, base_uom=UomCodeVO("G")),))
        for value in (None, [], ()):
            with self.assertRaises(InvalidPoolReservationConsumptionsError):
                self.apply_pool(value)
        with self.assertRaises(InvalidStockReservationConsumptionSnapshotError):
            self.apply_pool((self.a,))

    def test_both_consumers_require_strict_expected_versions(self) -> None:
        """Снимок погашения не отменяет ожидаемую версию текущего корня."""
        result = self.build()
        consumption = next(
            value for value in result if value.reservation_id == self.a.id
        )
        for version in (True, False, -1, None, Decimal(1), "1"):
            with self.assertRaises(InvalidStockReservationValueError):
                self.apply(self.a, consumption, expected_version=version)
            with self.assertRaises(InvalidAvailabilityPoolValueError):
                self.apply_pool(result, expected_version=version)
        for version in (0, 2):
            with self.assertRaises(StockReservationVersionConflictError):
                self.apply(self.a, consumption, expected_version=version)
            with self.assertRaises(AvailabilityPoolVersionConflictError):
                self.apply_pool(result, expected_version=version)

    def test_binding_and_consumer_do_not_create_database_idempotency(self) -> None:
        """Старый снимок устаревает, но повторное построение по новому состоянию требует дедупликации хранения."""
        original = next(
            value for value in self.build() if value.reservation_id == self.b.id
        )
        changed = self.apply(self.b, original)
        with self.assertRaises(StockReservationVersionConflictError):
            self.apply(changed, original)
        rebuilt = self.build(
            reservations=(self.a.execution_snapshot(), changed.execution_snapshot())
        )
        repeated = self.apply(
            changed,
            next(value for value in rebuilt if value.reservation_id == self.b.id),
        )
        self.assertEqual(
            (repeated.consumed_qty.value, repeated.reserved_qty.value),
            (Decimal(2), Decimal(2)),
        )

    def test_full_document_execution_and_binding_path_uses_real_domain_factories(
        self,
    ) -> None:
        """Подтверждённый план и созданное исполнение дают те же погашения без изменения прогресса."""
        document = StockDocument.create(
            identifier=StockDocumentIdVO(uuid4()),
            operation_type=StockOperationType.ISSUE,
            warehouse=self.warehouse,
            owner_id=self.owner,
            created_at=self.created,
        )
        line = StockDocumentLine.create(
            identifier=StockDocumentLineIdVO(uuid4()),
            inventory_item=self.item.document_snapshot(),
            quantity=QuantityVO(Decimal(10)),
            uom=self.item.base_uom,
        )
        document = document.add_line(
            line, inventory_item=self.item.document_snapshot(), updated_at=self.created
        )
        confirmed = document.confirm(
            warehouse=self.warehouse,
            inventory_items=(self.item.document_snapshot(),),
            updated_at=self.created,
        )
        execution = StockExecution.create(
            identifier=StockExecutionIdVO(uuid4()),
            document=confirmed.execution_snapshot(),
            executed_at=self.time,
            lines=tuple(
                replace(value, document_line_id=line.id) for value in self.lines
            ),
            warehouse=self.warehouse,
            inventory_items=(self.item.execution_snapshot(),),
            locations=(self.location,),
        )
        result = self.build(execution=execution.reservation_snapshot())
        changed = {
            value.reservation_id: self.apply(
                self.a if value.reservation_id == self.a.id else self.b, value
            )
            for value in result
        }
        self.assertEqual(
            (
                changed[self.a.id].consumed_qty.value,
                changed[self.b.id].consumed_qty.value,
            ),
            (Decimal(5), Decimal(1)),
        )
        self.assertEqual(confirmed.lines[0].executed_qty.value, Decimal(0))
        self.assertEqual(self.pool.reserved_qty.value, Decimal(12))

    def test_multiple_items_and_pools_are_built_together_but_applied_separately(
        self,
    ) -> None:
        """Одно исполнение разных товаров сопоставляется по полным ключам и разделяется по пулам."""
        other_item_id = InventoryItemIdVO(uuid4())
        other_pool_id = AvailabilityPoolIdVO(uuid4())
        other_key = replace(self.pool.key, inventory_item_id=other_item_id)
        other_reservation = replace(self.b, key=other_key, pool_id=other_pool_id)
        line = self.lines[2]
        line = replace(
            line,
            inventory_item_id=other_item_id,
            route=IssueExecutionRouteVO(
                replace(line.route.source, inventory_item_id=other_item_id)
            ),
        )
        execution = replace(
            self.execution, lines=(*self.lines[:2], line, self.lines[3])
        )
        result = self.build(
            execution=execution.reservation_snapshot(),
            reservations=(
                self.a.execution_snapshot(),
                other_reservation.execution_snapshot(),
            ),
        )
        self.assertEqual(
            {value.pool_id for value in result}, {self.pool.id, other_pool_id}
        )
        with self.assertRaises(AvailabilityPoolConsumptionMismatchError):
            self.apply_pool(result)
        own = tuple(value for value in result if value.pool_id == self.pool.id)
        self.assertEqual(self.apply_pool(own).reserved_qty.value, Decimal(7))

    def test_serial_lines_stay_whole_and_multiple_instances_can_consume_one_reservation(
        self,
    ) -> None:
        """Для SERIAL каждая фактическая строка равна 1 PCS, мягкое погашение суммирует выбранные экземпляры."""
        item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("SERIAL"),
            base_uom=UomCodeVO("PCS"),
            quantity_rules=QuantityRulesVO(Decimal(1)),
            tracking_mode=TrackingMode.SERIAL,
        )
        pool = replace(
            self.pool,
            key=replace(self.pool.key, inventory_item_id=item.id),
            base_uom=item.base_uom,
        )
        reservation = StockReservation.create(
            identifier=StockReservationIdVO(uuid4()),
            pool=pool.reservation_snapshot(),
            inventory_item=item.stock_snapshot(),
            source_ref=self.a.source_ref,
            requested_qty=QuantityVO(Decimal(2)),
            created_at=self.created,
        )
        reservation = reservation.add_reserved(
            QuantityVO(Decimal(2)),
            expected_version=0,
            inventory_item=item.stock_snapshot(),
            updated_at=self.created,
        )
        lines = tuple(
            StockExecutionLine.create(
                identifier=StockExecutionLineIdVO(uuid4()),
                document_line_id=StockDocumentLineIdVO(uuid4()),
                inventory_item=item.execution_snapshot(),
                quantity=QuantityVO(Decimal(1)),
                uom=item.base_uom,
                route=IssueExecutionRouteVO(
                    replace(
                        self.position.dimensions,
                        inventory_item_id=item.id,
                        serial_id=StockSerialIdVO(uuid4()),
                    )
                ),
            )
            for _ in range(2)
        )
        execution = replace(self.execution, lines=lines)
        result = self.build(
            execution=execution.reservation_snapshot(),
            bindings=tuple(
                ReservationExecutionBindingVO(value.id, reservation.id)
                for value in lines
            ),
            reservations=(reservation.execution_snapshot(),),
        )
        self.assertEqual(result[0].quantity.value, Decimal(2))
        changed = self.apply(
            reservation, result[0], inventory_item=item.stock_snapshot()
        )
        self.assertEqual(changed.status, StockReservationStatus.CONSUMED)

    def test_hostile_decimal_context_does_not_round_build_or_pool_sum(self) -> None:
        """Сумма по строкам и затем по резервам точна при низкой внешней точности и активных traps."""
        lines = (
            self.line("12345678901234567890.10"),
            self.line("0.05"),
            self.line("1"),
            self.line("4"),
        )
        execution = replace(self.execution, lines=lines)
        bindings = tuple(
            ReservationExecutionBindingVO(
                value.id, self.a.id if index < 2 else self.b.id
            )
            for index, value in enumerate(lines[:3])
        )
        pool = replace(
            self.pool, reserved_qty=QuantityVO(Decimal("12345678901234567891.15"))
        )
        with localcontext() as context:
            context.prec = 2
            context.Emax = 2
            context.Emin = -2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            result = self.build(
                execution=execution.reservation_snapshot(), bindings=bindings
            )
            a = next(value for value in result if value.reservation_id == self.a.id)
            self.assertEqual(a.quantity.value, Decimal("12345678901234567890.15"))
            after = pool.consume_reservations(
                result,
                expected_version=pool.version,
                **(self.context() | dict(positions=(), locations=())),
            )
            self.assertEqual(after.reserved_qty.value, Decimal(0))
            self.assertFalse(any(context.flags.values()))

    def test_unrepresentable_grouped_sum_is_controlled_domain_error(self) -> None:
        """Группировка не округляет количество при превышении защитного предела точной арифметики."""
        lines = (self.line("1E+1000001"), self.line("1"))
        execution = replace(self.execution, lines=lines)
        with self.assertRaises(StockQuantityArithmeticError):
            self.build(
                execution=execution.reservation_snapshot(),
                bindings=tuple(
                    ReservationExecutionBindingVO(value.id, self.a.id)
                    for value in lines
                ),
                reservations=(self.a.execution_snapshot(),),
            )

    def test_pool_keeps_counter_limit_and_allows_deficit_after_physical_issue(
        self,
    ) -> None:
        """Группировка сохраняет предел общего удержания и не запрещает дефицит других обязательств."""
        result = self.build()
        original = self.pool
        self.pool = replace(original, reserved_qty=QuantityVO(Decimal(5)))
        with self.assertRaises(ExcessiveReservationConsumptionError):
            self.apply_pool(result)
        self.pool = original
        changed = self.apply_pool(result, positions=(), locations=())
        self.assertEqual(
            (
                changed.eligible_qty.value,
                changed.reserved_qty.value,
                changed.deficit_qty.value,
            ),
            (Decimal(0), Decimal(6), Decimal(6)),
        )

    def test_failed_consumer_leaves_all_originals_unchanged(self) -> None:
        """Успешно подготовленный кандидат не означает частичное сохранение при ошибке другого корня."""
        result = self.build()
        candidate = self.apply_pool(result)
        too_small = replace(
            self.a,
            reserved_qty=QuantityVO(Decimal(1)),
            status=StockReservationStatus.PARTIALLY_RESERVED,
        )
        with self.assertRaises(StockReservationConsumptionExceededError):
            self.apply(
                too_small,
                next(value for value in result if value.reservation_id == self.a.id),
            )
        self.assertEqual(candidate.reserved_qty.value, Decimal(6))
        self.assertEqual(
            (
                self.pool.reserved_qty.value,
                self.a.reserved_qty.value,
                self.a.consumed_qty.value,
                self.position.on_hand_qty.value,
            ),
            (Decimal(12), Decimal(8), Decimal(0), Decimal(20)),
        )


if __name__ == "__main__":
    unittest.main()
