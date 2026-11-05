"""Запуск инвентаризации, отдельное учётное основание и обнаружение параллельных движений."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from src.modules.inventory.domain.inventory_count.aggregate import InventoryCount
from src.modules.inventory.domain.inventory_count.baseline_snapshot import (
    InventoryCountBaselineSnapshot,
)
from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountBaselineError,
    InvalidInventoryCountStartPlanError,
    InvalidInventoryCountValueError,
    InventoryCountBaselineChangedError,
    InventoryCountContextMismatchError,
    InventoryCountStatusError,
    InventoryCountTimeError,
    InventoryCountVersionConflictError,
)
from src.modules.inventory.domain.inventory_count.value_object.baseline_id import (
    InventoryCountBaselineIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.baseline_ref import (
    InventoryCountBaselineRefVO,
)
from src.modules.inventory.domain.inventory_count.value_object.count_type import (
    CountType,
)
from src.modules.inventory.domain.inventory_count.value_object.identifier import (
    InventoryCountIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.scope import CountScopeVO
from src.modules.inventory.domain.inventory_count.value_object.status import (
    InventoryCountStatus,
)
from src.modules.inventory.domain.inventory_item.aggregate import InventoryItem
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.policy.inventory_count_baseline import (
    InventoryCountBaselinePolicy,
)
from src.modules.inventory.domain.policy.inventory_count_start import (
    InventoryCountStartPolicy,
)
from src.modules.inventory.domain.stock_location.error import StockLocationInactiveError
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
from src.modules.inventory.domain.stock_position.error import (
    InvalidSerialStockQuantityError,
    InvalidStockPositionCountingSnapshotError,
    InvalidStockPositionValueError,
    InvalidStockPositionSnapshotError,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
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
from src.modules.inventory.domain.warehouse.error import (
    InvalidWarehouseSnapshotError,
    WarehouseInactiveError,
)
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class InventoryCountStartDomainTests(unittest.TestCase):
    """Проверяет запуск без изменения запасов и консервативный контроль полного основания."""

    def setUp(self) -> None:
        """Готовит подтверждённый план и физическую позицию 100 PCS версии 7."""
        self.time = datetime(2026, 11, 5, 12, tzinfo=UTC)
        self.warehouse = WarehouseSnapshot(WarehouseIdVO(uuid4()), True, None)
        self.owner = StockOwnerIdVO(uuid4())
        self.location = StockLocationSnapshot(
            StockLocationIdVO(uuid4()), self.warehouse.id, LocationType.STORAGE, True
        )
        self.other_location = replace(
            self.location,
            id=StockLocationIdVO(uuid4()),
            location_type=LocationType.QUARANTINE,
        )
        self.locations = (self.location, self.other_location)
        self.item = InventoryItem.create(
            identifier=InventoryItemIdVO(uuid4()),
            sku=SkuVO("COUNT-START"),
            base_uom=UomCodeVO("PCS"),
            quantity_rules=QuantityRulesVO(Decimal(1)),
        )
        self.dimensions = StockDimensionsVO(
            self.item.id, self.location.id, self.owner, None, None, StockStatus.SELLABLE
        )
        self.position = StockPosition.restore(
            identifier=StockPositionIdVO(uuid4()),
            dimensions=self.dimensions,
            base_uom=UomCodeVO("PCS"),
            on_hand_qty=QuantityVO(Decimal(100)),
            version=7,
        )
        self.count = self.confirmed()
        self.baseline = self.build()

    def confirmed(self, scope: CountScopeVO | None = None) -> InventoryCount:
        """Создаёт и подтверждает полный либо частичный план без начала пересчёта."""
        draft = InventoryCount.create(
            identifier=InventoryCountIdVO(uuid4()),
            warehouse=self.warehouse,
            owner_id=self.owner,
            scope=scope or CountScopeVO(CountType.FULL, ()),
            created_at=self.time,
        )
        return draft.confirm(
            expected_version=0,
            warehouse=self.warehouse,
            locations=(
                () if draft.scope.count_type is CountType.FULL else self.locations
            ),
            updated_at=self.time,
        )

    def build(self, **changes: object) -> InventoryCountBaselineSnapshot:
        """Строит отдельное основание для точной версии текущего подтверждённого плана."""
        return InventoryCountStartPolicy.build_baseline(
            **(
                dict(
                    plan=self.count.start_plan_snapshot(),
                    identifier=InventoryCountBaselineIdVO(uuid4()),
                    snapshot_at=self.time,
                    warehouse=self.warehouse,
                    locations=self.locations,
                    positions=(self.position.counting_snapshot(),),
                )
                | changes
            )
        )

    def start(self, **changes: object) -> InventoryCount:
        """Запускает текущий план по основанию и актуальным снимкам адресов."""
        return self.count.start(
            **(
                dict(
                    baseline=self.baseline,
                    expected_version=self.count.version,
                    warehouse=self.warehouse,
                    locations=self.locations,
                    updated_at=self.time,
                )
                | changes
            )
        )

    def check(self, **changes: object) -> None:
        """Сравнивает полный текущий набор физических позиций с неизменяемым основанием."""
        InventoryCountBaselinePolicy.ensure_unchanged(
            **(
                dict(
                    baseline=self.baseline,
                    locations=self.locations,
                    positions=(self.position.counting_snapshot(),),
                )
                | changes
            )
        )

    def restore(self, reference: InventoryCount, **changes: object) -> InventoryCount:
        """Восстанавливает полный собственный состав без загрузки большого основания."""
        return InventoryCount.restore(
            **(
                dict(
                    identifier=reference.id,
                    warehouse_id=reference.warehouse_id,
                    owner_id=reference.owner_id,
                    scope=reference.scope,
                    status=reference.status,
                    baseline=reference.baseline,
                    created_at=reference.created_at,
                    updated_at=reference.updated_at,
                    version=reference.version,
                )
                | changes
            )
        )

    def test_start_keeps_large_baseline_outside_root_and_preserves_inputs(self) -> None:
        """Запуск меняет только статус, ссылку, время и версию корня; физический запас прежний."""
        before = self.count
        started = self.start()
        self.assertEqual(
            (started.status, started.version), (InventoryCountStatus.IN_PROGRESS, 2)
        )
        self.assertEqual(
            started.baseline, InventoryCountBaselineRefVO(self.baseline.id, self.time)
        )
        self.assertEqual(
            (before.status, before.version, before.baseline),
            (InventoryCountStatus.CONFIRMED, 1, None),
        )
        self.assertEqual(
            (self.position.on_hand_qty.value, self.position.version), (Decimal(100), 7)
        )
        self.assertNotIn("positions", {field.name for field in fields(started)})
        self.assertNotIn("locations", {field.name for field in fields(started)})
        self.assertEqual(self.baseline.inventory_count_version, before.version)

    def test_partial_start_uses_exact_addresses_and_all_physical_statuses(self) -> None:
        """Частичная проверка сохраняет выбранные адреса и несбываемый физический запас."""
        self.count = self.confirmed(
            CountScopeVO(CountType.PARTIAL, tuple(row.id for row in self.locations))
        )
        blocked = replace(
            self.position,
            dimensions=replace(
                self.dimensions,
                location_id=self.other_location.id,
                stock_status=StockStatus.BLOCKED,
            ),
        )
        # У второй физической комбинации собственный идентификатор позиции.
        self.baseline = self.build(
            positions=(
                self.position.counting_snapshot(),
                replace(blocked, id=StockPositionIdVO(uuid4())).counting_snapshot(),
            )
        )
        started = self.start(locations=tuple(reversed(self.locations)))
        self.assertEqual(started.scope, self.count.scope)
        self.assertEqual(self.baseline.positions[1].on_hand_qty.value, Decimal(100))

    def test_empty_full_and_partial_baselines_are_valid(self) -> None:
        """Пустые адреса и пустой склад можно пересчитывать без фиктивной позиции."""
        empty = self.build(positions=(), locations=())
        self.assertEqual(
            self.start(baseline=empty, locations=()).status,
            InventoryCountStatus.IN_PROGRESS,
        )
        self.count = self.confirmed(
            CountScopeVO(CountType.PARTIAL, tuple(row.id for row in self.locations))
        )
        self.baseline = self.build(positions=())
        self.assertEqual(self.start().status, InventoryCountStatus.IN_PROGRESS)

    def test_full_start_includes_inactive_location_stock_without_sale_filter(
        self,
    ) -> None:
        """Неактивный адрес с физическим запасом не исчезает из полной инвентаризации."""
        locations = (replace(self.location, is_active=False), self.other_location)
        baseline = self.build(locations=locations)
        self.assertEqual(
            self.start(baseline=baseline, locations=locations).status,
            InventoryCountStatus.IN_PROGRESS,
        )
        self.assertEqual(baseline.positions[0].on_hand_qty.value, Decimal(100))

    def test_partial_rechecks_location_activity_at_build_and_at_start(self) -> None:
        """Подтверждение не освобождает от проверки активности выбранных адресов перед запуском."""
        self.count = self.confirmed(
            CountScopeVO(CountType.PARTIAL, tuple(row.id for row in self.locations))
        )
        self.baseline = self.build()
        inactive = (replace(self.location, is_active=False), self.other_location)
        with self.assertRaises(StockLocationInactiveError):
            self.build(locations=inactive)
        with self.assertRaises(StockLocationInactiveError):
            self.start(locations=inactive)

    def test_start_requires_confirmed_status_and_cannot_be_repeated(self) -> None:
        """Нельзя запускать черновик, отменённый план или уже начатую проверку."""
        for status in (InventoryCountStatus.DRAFT, InventoryCountStatus.CANCELLED):
            count = self.restore(self.count, status=status)
            with self.subTest(status=status):
                with self.assertRaises(InventoryCountStatusError):
                    count.start(
                        self.baseline,
                        expected_version=count.version,
                        warehouse=self.warehouse,
                        locations=self.locations,
                        updated_at=self.time,
                    )
                with self.assertRaises(InventoryCountStatusError):
                    self.build(plan=count.start_plan_snapshot())
        started = self.start()
        with self.assertRaises(InventoryCountStatusError):
            started.start(
                self.baseline,
                expected_version=started.version,
                warehouse=self.warehouse,
                locations=self.locations,
                updated_at=self.time,
            )
        with self.assertRaises(InventoryCountStatusError):
            started.cancel(expected_version=started.version, updated_at=self.time)
        with self.assertRaises(InventoryCountStatusError):
            started.change_scope(
                started.scope, expected_version=started.version, updated_at=self.time
            )
        with self.assertRaises(InventoryCountStatusError):
            started.confirm(
                expected_version=started.version,
                warehouse=self.warehouse,
                updated_at=self.time,
            )

    def test_start_rejects_stale_and_noninteger_versions_before_mutation(self) -> None:
        """Текущая и ожидаемая версии строго целые, без bool, устаревший результат не применяется."""
        with self.assertRaises(InventoryCountVersionConflictError):
            self.start(expected_version=0)
        for value in (True, -1, "1", Decimal(1), None):
            with self.subTest(value=value):
                with self.assertRaises(InvalidInventoryCountValueError):
                    self.start(expected_version=value)
                forged = replace(self.count, version=value)
                with self.assertRaises(InvalidInventoryCountValueError):
                    forged.start(
                        self.baseline,
                        expected_version=1,
                        warehouse=self.warehouse,
                        locations=self.locations,
                        updated_at=self.time,
                    )
        self.assertIsNone(self.count.baseline)

    def test_baseline_requires_exact_source_plan_version(self) -> None:
        """Версия основания равна версии плана до запуска, а после запуска остаётся исторической."""
        for value in (0, self.count.version + 1):
            with self.subTest(version=value):
                with self.assertRaises(InventoryCountVersionConflictError):
                    self.start(
                        baseline=replace(self.baseline, inventory_count_version=value)
                    )
        self.assertEqual(
            self.start().version, self.baseline.inventory_count_version + 1
        )

    def test_start_rejects_other_plan_and_scope_even_for_same_warehouse(self) -> None:
        """Совпадения склада недостаточно: нужны тот же план, владелец и область."""
        for baseline in (
            replace(self.baseline, inventory_count_id=InventoryCountIdVO(uuid4())),
            replace(
                self.baseline,
                scope=CountScopeVO(
                    CountType.PARTIAL, tuple(row.id for row in self.locations)
                ),
            ),
            replace(self.baseline, owner_id=StockOwnerIdVO(uuid4()), positions=()),
            replace(
                self.baseline,
                warehouse_id=WarehouseIdVO(uuid4()),
                locations=(),
                positions=(),
            ),
        ):
            with self.subTest(baseline=baseline):
                with self.assertRaises(InventoryCountContextMismatchError):
                    self.start(baseline=baseline)

    def test_start_rechecks_current_warehouse_and_full_location_membership(
        self,
    ) -> None:
        """Склад должен быть тем же активным, текущий набор адресов — соответствовать основанию."""
        for warehouse, error in (
            (replace(self.warehouse, is_active=False), WarehouseInactiveError),
            (
                replace(self.warehouse, id=WarehouseIdVO(uuid4())),
                InventoryCountContextMismatchError,
            ),
            (object(), InvalidWarehouseSnapshotError),
        ):
            with self.subTest(warehouse=warehouse):
                with self.assertRaises(error):
                    self.start(warehouse=warehouse)
        for locations in (
            (),
            (self.location,),
            (*self.locations, replace(self.location, id=StockLocationIdVO(uuid4()))),
        ):
            with self.subTest(locations=locations):
                with self.assertRaises(InventoryCountContextMismatchError):
                    self.start(locations=locations)

    def test_baseline_time_is_between_confirmation_and_start_registration(self) -> None:
        """Время снимка не подменяется моментом подтверждения и не может быть в будущем относительно запуска."""
        later = self.time + timedelta(minutes=5)
        baseline = self.build(snapshot_at=later)
        started = self.start(baseline=baseline, updated_at=later + timedelta(minutes=1))
        self.assertEqual(started.baseline.snapshot_at, later)
        with self.assertRaises(InventoryCountTimeError):
            self.start(baseline=baseline)
        with self.assertRaises(InventoryCountTimeError):
            self.build(snapshot_at=self.time - timedelta(seconds=1))
        confirmed_later = self.restore(self.count, updated_at=later)
        with self.assertRaises(InventoryCountTimeError):
            confirmed_later.start(
                self.baseline,
                expected_version=confirmed_later.version,
                warehouse=self.warehouse,
                locations=self.locations,
                updated_at=later,
            )

    def test_times_are_normalized_and_naive_inputs_rejected(self) -> None:
        """Явный пояс нормализуется в UTC; наивные даты не проходят фабрику, ссылку или запуск."""
        local = self.time.astimezone(timezone(timedelta(hours=2)))
        baseline = self.build(snapshot_at=local)
        started = self.start(baseline=baseline, updated_at=local)
        self.assertIs(baseline.snapshot_at.tzinfo, UTC)
        self.assertIs(started.baseline.snapshot_at.tzinfo, UTC)
        self.assertIs(
            InventoryCountBaselineRefVO(baseline.id, local).snapshot_at.tzinfo, UTC
        )
        for value in (self.time.replace(tzinfo=None), None, "now"):
            with self.subTest(value=value):
                with self.assertRaises(InventoryCountTimeError):
                    self.build(snapshot_at=value)
                with self.assertRaises(InventoryCountTimeError):
                    self.start(updated_at=value)
                with self.assertRaises(InventoryCountTimeError):
                    InventoryCountBaselineRefVO(baseline.id, value)

    def test_restore_requires_baseline_only_for_in_progress(self) -> None:
        """История запуска восстанавливается по компактной ссылке без текущих справочников или полного основания."""
        started = self.start()
        self.assertEqual(self.restore(started), started)
        with self.assertRaises(InvalidInventoryCountValueError):
            self.restore(started, baseline=None)
        for status in (
            InventoryCountStatus.DRAFT,
            InventoryCountStatus.CONFIRMED,
            InventoryCountStatus.CANCELLED,
        ):
            with self.subTest(status=status):
                with self.assertRaises(InvalidInventoryCountValueError):
                    self.restore(started, status=status)
        with self.assertRaises(InvalidInventoryCountValueError):
            self.restore(started, baseline=self.baseline)

    def test_restore_and_reference_reject_invalid_ids_and_chronology(self) -> None:
        """Нельзя восстановить ссылку с чужим типом ID или снимком вне собственной хронологии корня."""
        with self.assertRaises(InvalidInventoryCountBaselineError):
            InventoryCountBaselineRefVO(self.count.id, self.time)
        started = self.start()
        for time in (
            self.time - timedelta(seconds=1),
            self.time + timedelta(seconds=1),
        ):
            with self.subTest(time=time):
                with self.assertRaises(InventoryCountTimeError):
                    self.restore(
                        started,
                        baseline=InventoryCountBaselineRefVO(self.baseline.id, time),
                    )

    def test_baseline_header_and_plan_snapshots_validate_runtime_types(self) -> None:
        """Номинальные типы, UTC и строгие версии проверяются при прямом использовании снимков."""
        for field, value in (
            ("id", self.count.id),
            ("inventory_count_id", self.baseline.id),
            ("inventory_count_version", True),
            ("inventory_count_version", -1),
            ("warehouse_id", self.owner),
            ("owner_id", self.warehouse.id),
            ("scope", None),
            ("locations", list(self.locations)),
            ("positions", []),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaises(InvalidInventoryCountBaselineError):
                    replace(self.baseline, **{field: value}).ensure_valid()
        plan = self.count.start_plan_snapshot()
        for field, value in (
            ("id", self.owner),
            ("status", "CONFIRMED"),
            ("scope", None),
            ("version", True),
            ("version", -1),
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidInventoryCountStartPlanError):
                    self.build(plan=replace(plan, **{field: value}))
        local = self.time.astimezone(timezone(timedelta(hours=2)))
        with self.assertRaises(InvalidInventoryCountBaselineError):
            replace(self.baseline, snapshot_at=local).ensure_valid()
        with self.assertRaises(InvalidInventoryCountStartPlanError):
            self.build(plan=replace(plan, updated_at=local))

    def test_policies_and_start_reject_raw_roots_and_other_snapshot_families(
        self,
    ) -> None:
        """Прямые публичные вызовы не принимают корень, снимок продаж или произвольный объект вместо контракта."""
        with self.assertRaises(InvalidInventoryCountStartPlanError):
            self.build(plan=self.count)
        with self.assertRaises(InvalidInventoryCountBaselineError):
            self.start(baseline=self.count.start_plan_snapshot())
        with self.assertRaises(InvalidInventoryCountBaselineError):
            self.check(baseline=object())
        with self.assertRaises(InvalidInventoryCountBaselineError):
            self.build(positions=(self.position.availability_snapshot(),))

    def test_baseline_rejects_duplicate_locations_position_ids_and_dimensions(
        self,
    ) -> None:
        """Повторы не маскируются суммированием или словарём индекса актуальности."""
        snapshot = self.position.counting_snapshot()
        for locations, positions in (
            ((self.location, self.location), (snapshot,)),
            (self.locations, (snapshot, snapshot)),
            (
                self.locations,
                (snapshot, replace(snapshot, id=StockPositionIdVO(uuid4()))),
            ),
            (
                self.locations,
                (
                    snapshot,
                    replace(
                        snapshot,
                        dimensions=replace(
                            self.dimensions, stock_status=StockStatus.BLOCKED
                        ),
                    ),
                ),
            ),
        ):
            with self.subTest(locations=locations, positions=positions):
                with self.assertRaises(InvalidInventoryCountBaselineError):
                    self.build(locations=locations, positions=positions)

    def test_baseline_rejects_foreign_owners_locations_and_missing_partial_addresses(
        self,
    ) -> None:
        """Каждая позиция и каждый адрес должны принадлежать области и владельцу основания."""
        snapshot = self.position.counting_snapshot()
        for snapshot in (
            replace(
                snapshot,
                dimensions=replace(self.dimensions, owner_id=StockOwnerIdVO(uuid4())),
            ),
            replace(
                snapshot,
                dimensions=replace(
                    self.dimensions, location_id=StockLocationIdVO(uuid4())
                ),
            ),
        ):
            with self.assertRaises(InventoryCountContextMismatchError):
                self.build(positions=(snapshot,))
        with self.assertRaises(InventoryCountContextMismatchError):
            self.build(
                locations=(replace(self.location, warehouse_id=WarehouseIdVO(uuid4())),)
            )
        self.count = self.confirmed(
            CountScopeVO(CountType.PARTIAL, tuple(row.id for row in self.locations))
        )
        with self.assertRaises(InventoryCountContextMismatchError):
            self.build(locations=(self.location,))

    def test_counting_snapshot_retains_zero_quantity_and_strict_version(self) -> None:
        """Нулевая позиция остаётся в основании и участвует в проверке будущих изменений."""
        position = replace(self.position, on_hand_qty=QuantityVO(Decimal(0)))
        snapshot = position.counting_snapshot()
        snapshot.ensure_valid()
        self.assertEqual(
            (snapshot.on_hand_qty.value, snapshot.version), (Decimal(0), 7)
        )
        for value in (True, -1, "7", None):
            with self.subTest(value=value):
                with self.assertRaises(InvalidStockPositionCountingSnapshotError):
                    replace(snapshot, version=value).ensure_valid()
        with self.assertRaises(InvalidStockPositionValueError):
            replace(position, version=True).counting_snapshot()

    def test_serial_snapshot_accepts_only_zero_or_one_pcs(self) -> None:
        """Серийное основание хранит конкретный экземпляр и не допускает дробь, два экземпляра или KG."""
        snapshot = replace(
            self.position.counting_snapshot(),
            dimensions=replace(self.dimensions, serial_id=StockSerialIdVO(uuid4())),
        )
        for amount in ("0", "1"):
            replace(snapshot, on_hand_qty=QuantityVO(Decimal(amount))).ensure_valid()
        for amount in ("0.5", "2"):
            with self.assertRaises(InvalidSerialStockQuantityError):
                replace(
                    snapshot, on_hand_qty=QuantityVO(Decimal(amount))
                ).ensure_valid()
        with self.assertRaises(InvalidStockPositionSnapshotError):
            replace(
                snapshot, on_hand_qty=QuantityVO(Decimal(1)), base_uom=UomCodeVO("KG")
            ).ensure_valid()

    def test_baseline_preserves_separate_lots_serials_and_stock_statuses(self) -> None:
        """Одинаковый товар не объединяется между партиями, экземплярами и состояниями."""
        rows = tuple(
            replace(
                self.position.counting_snapshot(),
                id=StockPositionIdVO(uuid4()),
                dimensions=replace(
                    self.dimensions,
                    lot_id=StockLotIdVO(uuid4()),
                    serial_id=StockSerialIdVO(uuid4()),
                    stock_status=status,
                ),
                on_hand_qty=QuantityVO(Decimal(1)),
            )
            for status in StockStatus
        )
        baseline = self.build(positions=rows)
        self.assertEqual(baseline.positions, rows)
        self.assertEqual(
            self.start(baseline=baseline).status, InventoryCountStatus.IN_PROGRESS
        )
        InventoryCountBaselinePolicy.ensure_unchanged(
            baseline=baseline, locations=self.locations, positions=rows
        )
        changed = replace(
            rows[0],
            dimensions=replace(
                rows[0].dimensions,
                lot_id=StockLotIdVO(uuid4()),
                serial_id=StockSerialIdVO(uuid4()),
            ),
        )
        with self.assertRaises(InventoryCountBaselineChangedError):
            InventoryCountBaselinePolicy.ensure_unchanged(
                baseline=baseline,
                locations=self.locations,
                positions=(changed, *rows[1:]),
            )

    def test_unchanged_check_is_independent_of_input_order(self) -> None:
        """Порядок чтения адресов и позиций не меняет результат контроля актуальности."""
        other = replace(
            self.position,
            id=StockPositionIdVO(uuid4()),
            dimensions=replace(self.dimensions, location_id=self.other_location.id),
        )
        self.baseline = self.build(
            positions=(self.position.counting_snapshot(), other.counting_snapshot())
        )
        self.check(
            locations=tuple(reversed(self.locations)),
            positions=tuple(reversed(self.baseline.positions)),
        )

    def test_parallel_movement_and_round_trip_invalidate_old_baseline(self) -> None:
        """Отгрузка разрешена, но старый снимок 100/v7 не применим к 80/v8 или вернувшимся 100/v9."""
        started = self.start()
        current = self.position.apply_delta(
            StockDeltaVO(Decimal(-20)),
            inventory_item=self.item.stock_snapshot(),
            location=self.location,
            warehouse=self.warehouse,
        )
        with self.assertRaises(InventoryCountBaselineChangedError):
            self.check(positions=(current.counting_snapshot(),))
        returned = current.apply_delta(
            StockDeltaVO(Decimal(20)),
            inventory_item=self.item.stock_snapshot(),
            location=self.location,
            warehouse=self.warehouse,
        )
        self.assertEqual(returned.on_hand_qty, self.position.on_hand_qty)
        with self.assertRaises(InventoryCountBaselineChangedError):
            self.check(positions=(returned.counting_snapshot(),))
        self.assertEqual(started.baseline.id, self.baseline.id)
        self.assertEqual(self.baseline.positions[0].version, 7)

    def test_new_or_disappeared_positions_invalidate_including_empty_baseline(
        self,
    ) -> None:
        """Контроль сравнивает весь состав, а не только версии ранее известных ненулевых позиций."""
        with self.assertRaises(InventoryCountBaselineChangedError):
            self.check(positions=())
        extra = replace(
            self.position,
            id=StockPositionIdVO(uuid4()),
            dimensions=replace(self.dimensions, stock_status=StockStatus.DAMAGED),
            on_hand_qty=QuantityVO(Decimal(0)),
        )
        with self.assertRaises(InventoryCountBaselineChangedError):
            self.check(
                positions=(self.position.counting_snapshot(), extra.counting_snapshot())
            )
        self.baseline = self.build(positions=())
        self.check(positions=())
        with self.assertRaises(InventoryCountBaselineChangedError):
            self.check()

    def test_new_full_scope_location_and_position_cannot_be_hidden(self) -> None:
        """Полная проверка обнаруживает новую позицию на новом адресе и изменение набора адресов."""
        new_location = replace(self.location, id=StockLocationIdVO(uuid4()))
        extra = replace(
            self.position,
            id=StockPositionIdVO(uuid4()),
            dimensions=replace(self.dimensions, location_id=new_location.id),
        )
        for positions in (
            (self.position.counting_snapshot(),),
            (self.position.counting_snapshot(), extra.counting_snapshot()),
        ):
            with self.subTest(positions=positions):
                with self.assertRaises(InventoryCountBaselineChangedError):
                    self.check(
                        locations=(*self.locations, new_location), positions=positions
                    )

    def test_changed_dimensions_unit_or_quantity_cannot_hide_behind_same_version(
        self,
    ) -> None:
        """Кроме версии сравниваются идентичность, измерения, базовая единица и физическое количество."""
        snapshot = self.position.counting_snapshot()
        for current in (
            replace(snapshot, id=StockPositionIdVO(uuid4())),
            replace(snapshot, base_uom=UomCodeVO("KG")),
            replace(snapshot, on_hand_qty=QuantityVO(Decimal(99))),
            replace(
                snapshot,
                dimensions=replace(
                    self.dimensions, stock_status=StockStatus.QUARANTINE
                ),
            ),
        ):
            with self.subTest(current=current):
                with self.assertRaises(InventoryCountBaselineChangedError):
                    self.check(positions=(current,))

    def test_current_set_validation_precedes_unchanged_comparison(self) -> None:
        """Дубли или чужие снимки текущего чтения не сворачиваются в допустимый словарь."""
        snapshot = self.position.counting_snapshot()
        with self.assertRaises(InvalidInventoryCountBaselineError):
            self.check(positions=(snapshot, snapshot))
        with self.assertRaises(InvalidInventoryCountBaselineError):
            self.check(positions=(self.position,))
        with self.assertRaises(InventoryCountContextMismatchError):
            self.check(
                positions=(
                    replace(
                        snapshot,
                        dimensions=replace(
                            self.dimensions, owner_id=StockOwnerIdVO(uuid4())
                        ),
                    ),
                )
            )

    def test_baseline_reference_and_snapshots_are_immutable(self) -> None:
        """Основание, ссылка и снимок позиции не изменяются после запуска."""
        started = self.start()
        with self.assertRaises(FrozenInstanceError):
            self.baseline.positions = ()
        with self.assertRaises(FrozenInstanceError):
            started.baseline.snapshot_at = self.time + timedelta(hours=1)
        with self.assertRaises(FrozenInstanceError):
            self.baseline.positions[0].version = 8


if __name__ == "__main__":
    unittest.main()
