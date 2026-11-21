"""Найденный запас: новые измерения в ведомости без позиции, нулевое основание и повторная проверка контекста."""

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from test import test_inventory_count_sheet_domain as sheet_fixture
from src.modules.inventory.domain.count_sheet.aggregate import CountSheet
from src.modules.inventory.domain.count_sheet.entity.count_line import CountLine
from src.modules.inventory.domain.count_sheet.error import (
    InvalidCountLineError,
    InvalidCountSheetValueError,
    CountSheetLineConflictError,
    CountSheetSourceMismatchError,
    CountSheetStatusError,
    CountSheetTimeError,
    CountSheetVersionConflictError,
    UncountedCountSheetError,
)
from src.modules.inventory.domain.count_sheet.value_object.identifier import (
    CountSheetIdVO,
)
from src.modules.inventory.domain.count_sheet.value_object.line_id import CountLineIdVO
from src.modules.inventory.domain.count_sheet.value_object.line_origin import (
    CountLineOrigin,
)
from src.modules.inventory.domain.count_sheet.value_object.status import (
    CountSheetStatus,
)
from src.modules.inventory.domain.error import QuantityStepError
from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountBaselineError,
    InventoryCountBaselineChangedError,
    InventoryCountStatusError,
)
from src.modules.inventory.domain.inventory_count.value_object.count_type import (
    CountType,
)
from src.modules.inventory.domain.inventory_count.value_object.scope import CountScopeVO
from src.modules.inventory.domain.inventory_count.value_object.status import (
    InventoryCountStatus,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemStockSnapshotError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.found_count_line import FoundCountLinePolicy
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_lot.error import InvalidStockLotSnapshotError
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.stock_position.error import (
    InvalidStockPositionCountingSnapshotError,
    InvalidStockTrackingDimensionsError,
    StockDimensionsMismatchError,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_serial.error import (
    InvalidStockSerialSnapshotError,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.error import InvalidWarehouseSnapshotError
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class InventoryCountFoundStockDomainTests(unittest.TestCase):
    """Проверяет FOUND на полном неизменном основании с известными обычной и нулевой позициями."""

    def setUp(self) -> None:
        """Готовит ведомость BASELINE и новые измерения DAMAGED в уже зафиксированной локации."""
        self.f = sheet_fixture.InventoryCountSheetDomainTests()
        self.f.setUp()
        self.model = self.f.f
        self.count, self.baseline, self.sheet = (
            self.f.count,
            self.f.baseline,
            self.f.sheet,
        )
        self.time = self.f.time
        self.item = self.f.item
        self.location = self.model.other_location
        self.dimensions = replace(
            self.f.first.dimensions,
            location_id=self.location.id,
            stock_status=StockStatus.DAMAGED,
        )
        self.line_id = CountLineIdVO(uuid4())
        self.lot, self.serial = None, None

    def create(self, **changes: object) -> CountSheet:
        """Создаёт отдельную непустую ведомость с первой непосчитанной найденной строкой."""
        return CountSheet.create_with_found_line(
            **(
                dict(
                    identifier=CountSheetIdVO(uuid4()),
                    line_id=self.line_id,
                    inventory_count=self.count.sheet_source_snapshot(),
                    baseline=self.baseline,
                    dimensions=self.dimensions,
                    inventory_item=self.item,
                    warehouse=self.model.warehouse,
                    location=self.location,
                    created_at=self.time,
                    lot=self.lot,
                    serial=self.serial,
                )
                | changes
            )
        )

    def add(self, sheet: CountSheet | None = None, **changes: object) -> CountSheet:
        """Дополняет существующий черновик найденной строкой с явной версией и текущими снимками."""
        target = self.sheet if sheet is None else sheet
        arguments = dict(
            inventory_count=self.count.sheet_source_snapshot(),
            baseline=self.baseline,
            dimensions=self.dimensions,
            inventory_item=self.item,
            warehouse=self.model.warehouse,
            location=self.location,
            expected_version=target.version,
            updated_at=self.time,
            lot=self.lot,
            serial=self.serial,
        )
        identifier = changes.pop("identifier", self.line_id)
        return target.add_found_line(identifier, **(arguments | changes))

    def record(
        self, sheet: CountSheet, value: str = "5", **changes: object
    ) -> CountSheet:
        """Записывает факт найденной строки прежним методом ввода количества."""
        identifier = changes.pop("identifier", self.line_id)
        return sheet.record_count(
            identifier,
            **(
                dict(
                    counted_qty=QuantityVO(Decimal(value)),
                    counted_at=self.time,
                    inventory_item=self.item,
                    expected_version=sheet.version,
                    updated_at=self.time,
                )
                | changes
            ),
        )

    def submit(self, sheet: CountSheet, **changes: object) -> CountSheet:
        """Передаёт всё исходное основание и ровно необходимые карточки найденного запаса."""
        by_item = {
            self.f.item.inventory_item_id: self.f.item,
            self.item.inventory_item_id: self.item,
        }
        participating = {line.dimensions.inventory_item_id for line in sheet.lines}
        return sheet.submit(
            **(
                dict(
                    expected_version=sheet.version,
                    updated_at=self.time,
                    inventory_count=self.count.sheet_source_snapshot(),
                    baseline=self.baseline,
                    inventory_items=tuple(
                        value for key, value in by_item.items() if key in participating
                    ),
                    locations=self.baseline.locations,
                    positions=self.baseline.positions,
                    warehouse=self.model.warehouse,
                    lots=() if self.lot is None else (self.lot,),
                    serials=() if self.serial is None else (self.serial,),
                )
                | changes
            )
        )

    def tracked(self, mode: TrackingMode) -> None:
        """Готовит новый зарегистрированный товар с необходимыми ссылками на партию и экземпляр."""
        self.item = replace(
            self.item, inventory_item_id=InventoryItemIdVO(uuid4()), tracking_mode=mode
        )
        self.lot = (
            None
            if mode is TrackingMode.SERIAL
            else StockLotSnapshot(
                StockLotIdVO(uuid4()), self.item.inventory_item_id, StockDatesVO()
            )
        )
        self.serial = (
            None
            if mode is TrackingMode.LOT
            else StockSerialSnapshot(
                StockSerialIdVO(uuid4()),
                self.item.inventory_item_id,
                None if self.lot is None else self.lot.id,
            )
        )
        self.dimensions = replace(
            self.dimensions,
            inventory_item_id=self.item.inventory_item_id,
            lot_id=None if self.lot is None else self.lot.id,
            serial_id=None if self.serial is None else self.serial.id,
        )

    def test_factory_and_add_preserve_none_identity_and_initial_observation(
        self,
    ) -> None:
        """FOUND не создаёт фиктивную позицию, версию или нулевой факт вместо отсутствующего наблюдения."""
        created = self.create()
        added = self.add()
        for sheet in (created, added):
            with self.subTest(version=sheet.version):
                line = sheet.get_line(self.line_id)
                self.assertEqual(line.origin, CountLineOrigin.FOUND)
                self.assertIsNone(line.position_id)
                self.assertIsNone(line.position_version)
                self.assertIsNone(line.baseline_position_snapshot())
                self.assertEqual(line.expected_qty.value, Decimal(0))
                self.assertIsNone(line.counted_qty)
                self.assertIsNone(line.discrepancy)
        self.assertEqual((created.status, created.version), (CountSheetStatus.DRAFT, 0))
        self.assertEqual(added.version, 1)
        self.assertEqual(self.sheet.lines[0].origin, CountLineOrigin.BASELINE)
        self.assertEqual(len(self.sheet.lines), 1)

    def test_found_quantity_becomes_surplus_without_changing_any_stock(self) -> None:
        """Факт 5 образует расхождение +5, оставаясь наблюдением после передачи ведомости."""
        counted = self.record(self.create())
        submitted = self.submit(counted)
        self.assertEqual(submitted.status, CountSheetStatus.SUBMITTED)
        self.assertEqual(submitted.version, 2)
        self.assertEqual(submitted.lines[0].discrepancy.value, Decimal(5))
        self.assertEqual(self.baseline.positions, (self.f.first, self.f.second))
        self.assertEqual(self.model.position.on_hand_qty.value, Decimal(100))
        self.assertEqual(self.count.version, 2)
        self.assertIsNone(submitted.lines[0].position_id)

    def test_empty_book_with_existing_location_can_have_found_only_sheet(self) -> None:
        """Для пустого учётного набора не требуется создавать нулевую позицию перед пересчётом."""
        self.baseline = self.model.build(positions=())
        self.count = self.model.start(baseline=self.baseline)
        result = self.submit(self.record(self.create()))
        self.assertEqual(self.baseline.positions, ())
        self.assertEqual(result.lines[0].discrepancy.value, Decimal(5))
        with self.assertRaises(UncountedCountSheetError):
            self.submit(self.create())

    def test_multiple_found_lines_do_not_conflict_on_none_position_ids(self) -> None:
        """У нескольких найденных строк нет позиции, но ID строк и комбинации измерений различаются."""
        first = self.create()
        second_id = CountLineIdVO(uuid4())
        both = self.add(
            first,
            identifier=second_id,
            dimensions=replace(self.dimensions, stock_status=StockStatus.QUARANTINE),
        )
        both = self.record(both)
        both = self.record(both, "7", identifier=second_id)
        result = self.submit(both)
        self.assertEqual(len(result.lines), 2)
        self.assertEqual({line.position_id for line in result.lines}, {None})
        self.assertEqual(
            {line.discrepancy.value for line in result.lines}, {Decimal(5), Decimal(7)}
        )

    def test_mixed_sheet_requires_all_baseline_and_found_rows_counted(self) -> None:
        """Добавление найденной строки не позволяет пропустить исходную строку основания."""
        added = self.add()
        found_counted = self.record(added)
        with self.assertRaises(UncountedCountSheetError):
            self.submit(found_counted)
        complete = self.f.record(found_counted, "77")
        result = self.submit(complete)
        self.assertEqual(
            {line.discrepancy.value for line in result.lines},
            {Decimal(-23), Decimal(5)},
        )

    def test_zero_and_correction_use_existing_quantity_and_noop_rules(self) -> None:
        """Ноль — наблюдение; исправление не меняет нулевой учёт, повтор равного ввода не повышает версию."""
        draft = self.create()
        zero = self.record(draft, "0")
        self.assertEqual(zero.lines[0].discrepancy.value, Decimal(0))
        self.assertEqual(self.submit(zero).status, CountSheetStatus.SUBMITTED)
        self.assertIs(self.record(zero, "0"), zero)
        corrected = self.record(zero, "5")
        self.assertEqual(corrected.version, 2)
        self.assertEqual(corrected.lines[0].expected_qty.value, Decimal(0))

    def test_found_weight_is_counted_in_base_unit_with_current_step(self) -> None:
        """Новый товар с учётом KG вводится дробно и проверяется по своему шагу, без округления."""
        self.item = replace(
            self.item,
            inventory_item_id=InventoryItemIdVO(uuid4()),
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.05")),
        )
        self.dimensions = replace(
            self.dimensions, inventory_item_id=self.item.inventory_item_id
        )
        draft = self.create()
        with self.assertRaises(QuantityStepError):
            self.record(draft, "1.03")
        result = self.submit(self.record(draft, "1.05"))
        self.assertEqual(result.lines[0].base_uom, UomCodeVO("KG"))
        self.assertEqual(result.lines[0].discrepancy.value, Decimal("1.05"))
        with self.assertRaises(QuantityStepError):
            self.submit(
                self.record(draft, "1.05"),
                inventory_items=(
                    replace(self.item, quantity_rules=QuantityRulesVO(Decimal("0.1"))),
                ),
            )

    def test_full_scope_keeps_inactive_addresses_without_sale_filters(self) -> None:
        """Неактивный адрес из зафиксированной полной области остаётся местом физического наблюдения."""
        location = replace(self.location, is_active=False)
        draft = self.create(location=location)
        current_locations = tuple(
            location if row.id == location.id else row
            for row in self.baseline.locations
        )
        result = self.submit(self.record(draft), locations=current_locations)
        self.assertEqual(result.status, CountSheetStatus.SUBMITTED)

    def test_known_positive_and_zero_positions_cannot_be_recreated_as_found(
        self,
    ) -> None:
        """Проверяется всё основание: невыбранная нулевая позиция также запрещает FOUND с теми же измерениями."""
        for position in self.baseline.positions:
            location = next(
                row
                for row in self.baseline.locations
                if row.id == position.dimensions.location_id
            )
            with self.subTest(position=position.id):
                with self.assertRaises(CountSheetSourceMismatchError):
                    self.create(dimensions=position.dimensions, location=location)
                with self.assertRaises(CountSheetSourceMismatchError):
                    self.add(dimensions=position.dimensions, location=location)

    def test_duplicate_found_dimensions_and_line_ids_are_rejected(self) -> None:
        """Разные новые ID не разрешают посчитать одну комбинацию измерений дважды."""
        sheet = self.create()
        with self.assertRaises(CountSheetLineConflictError):
            self.add(sheet, identifier=CountLineIdVO(uuid4()))
        with self.assertRaises(CountSheetLineConflictError):
            self.add(
                sheet,
                dimensions=replace(
                    self.dimensions, stock_status=StockStatus.QUARANTINE
                ),
            )
        with self.assertRaises(CountSheetLineConflictError):
            self.add(identifier=self.f.binding.line_id)

    def test_foreign_owner_and_address_outside_frozen_scope_are_rejected(self) -> None:
        """FULL не расширяется на новые адреса после старта, владелец всегда берётся из основания."""
        for dimensions in (
            replace(self.dimensions, owner_id=StockOwnerIdVO(uuid4())),
            replace(self.dimensions, location_id=StockLocationIdVO(uuid4())),
        ):
            with self.subTest(dimensions=dimensions):
                with self.assertRaises(CountSheetSourceMismatchError):
                    self.create(dimensions=dimensions)
        self.baseline = self.model.build(positions=(), locations=())
        self.count = self.model.start(baseline=self.baseline, locations=())
        with self.assertRaises(CountSheetSourceMismatchError):
            self.create()

    def test_partial_scope_allows_only_explicitly_selected_address(self) -> None:
        """Частичная область проверяется по адресу из основания, без автоматического расширения."""
        confirmed = self.model.confirmed(
            CountScopeVO(
                CountType.PARTIAL, tuple(row.id for row in self.model.locations)
            )
        )
        self.baseline = self.model.build(
            plan=confirmed.start_plan_snapshot(),
            positions=(self.f.first, self.f.second),
        )
        self.count = confirmed.start(
            self.baseline,
            expected_version=confirmed.version,
            warehouse=self.model.warehouse,
            locations=self.model.locations,
            updated_at=self.time,
        )
        self.assertEqual(
            self.submit(self.record(self.create())).status, CountSheetStatus.SUBMITTED
        )
        other = replace(self.location, id=StockLocationIdVO(uuid4()))
        with self.assertRaises(CountSheetSourceMismatchError):
            self.create(
                location=other,
                dimensions=replace(self.dimensions, location_id=other.id),
            )

    def test_lot_context_and_new_lot_of_existing_item_are_validated(self) -> None:
        """Найденная партия требует согласованную карточку и проверяется повторно при передаче."""
        self.tracked(TrackingMode.LOT)
        draft = self.create()
        counted = self.record(draft)
        self.assertEqual(self.submit(counted).status, CountSheetStatus.SUBMITTED)
        with self.assertRaises(InvalidStockLotSnapshotError):
            self.create(lot=None)
        with self.assertRaises(StockDimensionsMismatchError):
            self.create(
                lot=replace(self.lot, inventory_item_id=InventoryItemIdVO(uuid4()))
            )
        with self.assertRaises(StockDimensionsMismatchError):
            self.submit(
                counted,
                lots=(replace(self.lot, inventory_item_id=InventoryItemIdVO(uuid4())),),
            )

    def test_serial_and_lot_serial_counts_are_zero_or_one(self) -> None:
        """Конкретный найденный экземпляр не превращается в дробное или групповое количество."""
        for mode in (TrackingMode.SERIAL, TrackingMode.LOT_AND_SERIAL):
            self.tracked(mode)
            with self.subTest(mode=mode):
                draft = self.create()
                for actual in ("0", "1"):
                    self.assertEqual(
                        self.submit(self.record(draft, actual)).status,
                        CountSheetStatus.SUBMITTED,
                    )
                with self.assertRaises(InvalidCountLineError):
                    self.record(draft, "2")
                with self.assertRaises(QuantityStepError):
                    self.record(draft, "0.5")
                with self.assertRaises(InvalidStockSerialSnapshotError):
                    self.create(serial=None)

    def test_new_lot_of_known_tracked_item_is_not_a_duplicate_of_old_lot(self) -> None:
        """Новый LOT того же товара образует новые измерения, не подменяя старую партию основания."""
        self.item = replace(self.item, tracking_mode=TrackingMode.LOT)
        old_lot = StockLotSnapshot(
            StockLotIdVO(uuid4()), self.item.inventory_item_id, StockDatesVO()
        )
        known = replace(
            self.f.first, dimensions=replace(self.f.first.dimensions, lot_id=old_lot.id)
        )
        self.baseline = self.model.build(positions=(known,))
        self.count = self.model.start(baseline=self.baseline)
        self.lot = replace(old_lot, id=StockLotIdVO(uuid4()))
        self.dimensions = replace(known.dimensions, lot_id=self.lot.id)
        self.location = self.model.location
        result = self.submit(self.record(self.create()))
        self.assertEqual(result.lines[0].dimensions.lot_id, self.lot.id)
        self.assertEqual(self.baseline.positions[0].dimensions.lot_id, old_lot.id)

    def test_multiple_found_rows_can_share_one_current_lot_snapshot(self) -> None:
        """Одна карточка партии обслуживает разные найденные состояния без повторной передачи снимка."""
        self.tracked(TrackingMode.LOT)
        sheet = self.create()
        second_id = CountLineIdVO(uuid4())
        sheet = self.add(
            sheet,
            identifier=second_id,
            dimensions=replace(self.dimensions, stock_status=StockStatus.QUARANTINE),
        )
        sheet = self.record(sheet)
        sheet = self.record(sheet, "7", identifier=second_id)
        submitted = self.submit(sheet)
        self.assertEqual(
            {line.dimensions.lot_id for line in submitted.lines}, {self.lot.id}
        )
        self.assertEqual(len(submitted.lines), 2)

    def test_serial_links_to_item_and_lot_are_checked_at_creation_and_submission(
        self,
    ) -> None:
        """Согласованные ID строки недостаточны, если текущий снимок экземпляра относится к другому товару или партии."""
        self.tracked(TrackingMode.LOT_AND_SERIAL)
        counted = self.record(self.create(), "1")
        for serial in (
            replace(self.serial, inventory_item_id=InventoryItemIdVO(uuid4())),
            replace(self.serial, lot_id=StockLotIdVO(uuid4())),
        ):
            with self.subTest(serial=serial):
                with self.assertRaises(StockDimensionsMismatchError):
                    self.create(serial=serial)
                with self.assertRaises(StockDimensionsMismatchError):
                    self.submit(counted, serials=(serial,))

    def test_submission_requires_exact_unique_lot_and_serial_context(self) -> None:
        """Пропущенные, повторные, лишние и нетипизированные карточки не подставляются по порядку."""
        self.tracked(TrackingMode.LOT_AND_SERIAL)
        counted = self.record(self.create(), "1")
        extra_lot = replace(self.lot, id=StockLotIdVO(uuid4()))
        extra_serial = replace(self.serial, id=StockSerialIdVO(uuid4()))
        for changes in (
            dict(lots=()),
            dict(serials=()),
            dict(lots=(self.lot, self.lot)),
            dict(serials=(self.serial, self.serial)),
            dict(lots=(self.lot, extra_lot)),
            dict(serials=(self.serial, extra_serial)),
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(CountSheetSourceMismatchError):
                    self.submit(counted, **changes)
        with self.assertRaises(InvalidStockLotSnapshotError):
            self.submit(counted, lots=[self.lot])
        with self.assertRaises(InvalidStockSerialSnapshotError):
            self.submit(counted, serials=[self.serial])

    def test_warehouse_and_location_context_are_rechecked_without_creating_cards(
        self,
    ) -> None:
        """Снимки должны обозначать склад ведомости и тот же адрес, а не произвольные совпадающие поля."""
        draft = self.create()
        with self.assertRaises(StockDimensionsMismatchError):
            self.create(
                location=replace(self.location, warehouse_id=WarehouseIdVO(uuid4()))
            )
        with self.assertRaises(StockDimensionsMismatchError):
            self.create(
                inventory_item=replace(
                    self.item, inventory_item_id=InventoryItemIdVO(uuid4())
                )
            )
        counted = self.record(draft)
        with self.assertRaises(InvalidWarehouseSnapshotError):
            self.submit(counted, warehouse=None)
        with self.assertRaises(CountSheetSourceMismatchError):
            self.submit(
                counted,
                warehouse=replace(self.model.warehouse, id=WarehouseIdVO(uuid4())),
            )

    def test_new_book_position_even_zero_invalidates_found_submission(self) -> None:
        """Конкурентное появление позиции не превращает FOUND в обычную строку и не приводит к двойному приходу."""
        counted = self.record(self.create())
        for amount in ("0", "5"):
            current = StockPositionCountingSnapshot(
                StockPositionIdVO(uuid4()),
                self.dimensions,
                self.item.base_uom,
                QuantityVO(Decimal(amount)),
                0,
            )
            with self.subTest(amount=amount):
                with self.assertRaises(InventoryCountBaselineChangedError):
                    self.submit(counted, positions=(*self.baseline.positions, current))
        self.assertEqual(counted.status, CountSheetStatus.DRAFT)
        self.assertIsNone(counted.lines[0].position_id)
        self.assertEqual(counted.lines[0].counted_qty.value, Decimal(5))

    def test_adding_rechecks_running_parent_and_original_baseline(self) -> None:
        """Нельзя дополнить чужую ведомость или начать найденную строку после выхода родителя из IN_PROGRESS."""
        stopped = replace(
            self.count.sheet_source_snapshot(),
            status=InventoryCountStatus.CANCELLED,
            baseline=None,
        )
        with self.assertRaises(InventoryCountStatusError):
            self.create(inventory_count=stopped)
        with self.assertRaises(InventoryCountStatusError):
            self.add(inventory_count=stopped)
        with self.assertRaises(CountSheetSourceMismatchError):
            self.add(baseline=self.model.build(positions=self.baseline.positions))

    def test_add_requires_draft_strict_version_and_ordered_time(self) -> None:
        """Новый состав создаётся только реальным переходом черновика с актуальной версией."""
        for version in (True, -1, "0", None):
            with self.subTest(version=version):
                with self.assertRaises(InvalidCountSheetValueError):
                    self.add(expected_version=version)
        with self.assertRaises(CountSheetVersionConflictError):
            self.add(expected_version=2)
        with self.assertRaises(CountSheetTimeError):
            self.add(updated_at=self.time - timedelta(seconds=1))
        with self.assertRaises(CountSheetTimeError):
            self.create(created_at=self.time - timedelta(seconds=1))
        later = self.time + timedelta(seconds=1)
        with self.assertRaises(CountSheetTimeError):
            self.add(
                inventory_count=replace(
                    self.count.sheet_source_snapshot(), updated_at=later
                )
            )
        for sheet in (
            self.submit(self.record(self.create())),
            self.create().cancel(expected_version=0, updated_at=self.time),
        ):
            with self.subTest(status=sheet.status):
                with self.assertRaises(CountSheetStatusError):
                    self.add(sheet)

    def test_restore_enforces_origin_matrix_and_keeps_found_observation(self) -> None:
        """FOUND восстанавливается без позиции, ненулевого учёта или придуманной версии."""
        counted = self.record(self.create())
        restored = self.f.restore(counted)
        self.assertEqual(restored, counted)
        line = restored.lines[0]
        for changed in (
            replace(line, position_id=StockPositionIdVO(uuid4())),
            replace(line, position_version=0),
            replace(line, position_version=False),
            replace(line, expected_qty=QuantityVO(Decimal(1))),
            replace(line, origin="FOUND"),
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(InvalidCountLineError):
                    self.f.restore(counted, lines=(changed,))
        with self.assertRaises(InvalidStockPositionCountingSnapshotError):
            replace(line, origin=CountLineOrigin.BASELINE).ensure_valid()
        submitted = self.submit(counted)
        self.assertEqual(self.f.restore(submitted), submitted)

    def test_origin_change_cannot_launder_known_zero_position(self) -> None:
        """Локально корректный FOUND с нулём всё равно отклоняется, если его измерения есть в полном основании."""
        known = CountLine.create(identifier=self.line_id, position=self.f.second)
        forged = replace(
            known, origin=CountLineOrigin.FOUND, position_id=None, position_version=None
        )
        forged.ensure_valid()
        sheet = self.f.restore(self.sheet, lines=(forged,))
        counted = self.record(sheet, "5")
        with self.assertRaises(CountSheetSourceMismatchError):
            self.submit(counted)

    def test_restore_and_submission_reject_duplicate_found_dimensions(self) -> None:
        """Отсутствие ID позиции не отключает проверку уникальности измерений."""
        sheet = self.create()
        line = sheet.lines[0]
        with self.assertRaises(CountSheetLineConflictError):
            self.f.restore(
                sheet, lines=(line, replace(line, id=CountLineIdVO(uuid4())))
            )
        with self.assertRaises(CountSheetLineConflictError):
            FoundCountLinePolicy.ensure_sources(
                lines=(line, line), baseline=self.baseline
            )

    def test_found_expected_snapshot_never_contains_fake_position(self) -> None:
        """Найденные измерения остаются отдельным источником и в дочерней фабрике восстановления."""
        source = self.create().lines[0]
        line = CountLine.restore(
            identifier=source.id,
            origin=CountLineOrigin.FOUND,
            position_id=None,
            position_version=None,
            dimensions=source.dimensions,
            base_uom=source.base_uom,
            expected_qty=source.expected_qty,
            counted_qty=None,
            counted_at=None,
        )
        self.assertIsNone(line.baseline_position_snapshot())
        self.assertEqual(line, source)
        with self.assertRaises(FrozenInstanceError):
            line.origin = CountLineOrigin.BASELINE

    def test_public_policy_contracts_reject_wrong_types_and_unneeded_contexts(
        self,
    ) -> None:
        """Политика не принимает корни, произвольные списки или снимки другого назначения."""
        with self.assertRaises(InvalidInventoryItemStockSnapshotError):
            self.create(inventory_item=self.model.item)
        with self.assertRaises(InvalidInventoryCountBaselineError):
            FoundCountLinePolicy.ensure_sources(lines=(), baseline=object())
        with self.assertRaises(InvalidCountLineError):
            FoundCountLinePolicy.ensure_sources(
                lines=[self.create().lines[0]], baseline=self.baseline
            )
        with self.assertRaises(InvalidCountLineError):
            FoundCountLinePolicy.ensure_sources(
                lines=self.sheet.lines, baseline=self.baseline
            )
        with self.assertRaises(InvalidStockTrackingDimensionsError):
            self.create(
                lot=StockLotSnapshot(
                    StockLotIdVO(uuid4()), self.item.inventory_item_id, StockDatesVO()
                )
            )
        baseline_only = self.f.record()
        with self.assertRaises(CountSheetSourceMismatchError):
            self.submit(
                baseline_only,
                lots=(
                    StockLotSnapshot(
                        StockLotIdVO(uuid4()),
                        self.item.inventory_item_id,
                        StockDatesVO(),
                    ),
                ),
            )


if __name__ == "__main__":
    unittest.main()
