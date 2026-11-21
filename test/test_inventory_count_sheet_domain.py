"""Ведомости пересчёта: фиксированное основание, наблюдения, расхождения и передача без изменения запасов."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_count_start_domain as count_fixture
from src.modules.inventory.domain.count_sheet.aggregate import CountSheet
from src.modules.inventory.domain.count_sheet.entity.count_line import CountLine
from src.modules.inventory.domain.count_sheet.error import (
    InvalidCountLineError,
    InvalidCountSheetLineBindingError,
    InvalidCountSheetValueError,
    CountSheetLineConflictError,
    CountSheetLineNotFoundError,
    CountSheetSourceMismatchError,
    CountSheetStatusError,
    CountSheetTimeError,
    CountSheetVersionConflictError,
    UncountedCountSheetError,
)
from src.modules.inventory.domain.count_sheet.value_object.identifier import (
    CountSheetIdVO,
)
from src.modules.inventory.domain.count_sheet.value_object.line_binding import (
    CountSheetLineBindingVO,
)
from src.modules.inventory.domain.count_sheet.value_object.line_id import CountLineIdVO
from src.modules.inventory.domain.count_sheet.value_object.status import (
    CountSheetStatus,
)
from src.modules.inventory.domain.error import InvalidQuantityError, QuantityStepError
from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountBaselineError,
    InvalidInventoryCountSheetSourceError,
    InventoryCountBaselineChangedError,
    InventoryCountStatusError,
)
from src.modules.inventory.domain.inventory_count.value_object.baseline_ref import (
    InventoryCountBaselineRefVO,
)
from src.modules.inventory.domain.inventory_count.value_object.baseline_id import (
    InventoryCountBaselineIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.identifier import (
    InventoryCountIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.scope import CountScopeVO
from src.modules.inventory.domain.inventory_count.value_object.count_type import (
    CountType,
)
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
from src.modules.inventory.domain.policy.count_sheet_source import (
    CountSheetSourcePolicy,
)
from src.modules.inventory.domain.policy.count_sheet_line import CountSheetLinePolicy
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_position.error import (
    InvalidStockPositionCountingSnapshotError,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class InventoryCountSheetDomainTests(unittest.TestCase):
    """Проверяет отдельную ведомость на одну из двух позиций основания без привязки к SQL или API."""

    def setUp(self) -> None:
        """Готовит запущенную полную инвентаризацию с 100 PCS/v7 и второй нулевой позицией."""
        self.f = count_fixture.InventoryCountStartDomainTests()
        self.f.setUp()
        self.time = self.f.time
        self.first = self.f.position.counting_snapshot()
        self.second = replace(
            self.first,
            id=StockPositionIdVO(uuid4()),
            dimensions=replace(
                self.first.dimensions,
                location_id=self.f.other_location.id,
                stock_status=StockStatus.BLOCKED,
            ),
            on_hand_qty=QuantityVO(Decimal(0)),
            version=0,
        )
        self.baseline = self.f.build(positions=(self.first, self.second))
        self.count = self.f.start(baseline=self.baseline)
        self.binding = CountSheetLineBindingVO(CountLineIdVO(uuid4()), self.first.id)
        self.second_binding = CountSheetLineBindingVO(
            CountLineIdVO(uuid4()), self.second.id
        )
        self.item = self.f.item.stock_snapshot()
        self.sheet = self.create()

    def create(self, **changes: object) -> CountSheet:
        """Создаёт ведомость только на первую позицию, оставляя вторую вне выбранных строк."""
        return CountSheet.create_from_baseline(
            **(
                dict(
                    identifier=CountSheetIdVO(uuid4()),
                    inventory_count=self.count.sheet_source_snapshot(),
                    baseline=self.baseline,
                    bindings=(self.binding,),
                    created_at=self.time,
                )
                | changes
            )
        )

    def record(
        self, sheet: CountSheet | None = None, value: str = "77", **changes: object
    ) -> CountSheet:
        """Вводит наблюдение в базовой единице по текущей версии ведомости."""
        target = self.sheet if sheet is None else sheet
        arguments = dict(
            counted_qty=QuantityVO(Decimal(value)),
            counted_at=self.time,
            inventory_item=self.item,
            expected_version=target.version,
            updated_at=self.time,
        )
        identifier = changes.pop("identifier", self.binding.line_id)
        return target.record_count(identifier, **(arguments | changes))

    def submit(self, sheet: CountSheet, **changes: object) -> CountSheet:
        """Передаёт полный текущий состав основания, включая невыбранную нулевую позицию."""
        return sheet.submit(
            **(
                dict(
                    expected_version=sheet.version,
                    updated_at=self.time,
                    inventory_count=self.count.sheet_source_snapshot(),
                    baseline=self.baseline,
                    inventory_items=(self.item,),
                    locations=self.f.locations,
                    positions=self.baseline.positions,
                )
                | changes
            )
        )

    def restore(self, sheet: CountSheet, **changes: object) -> CountSheet:
        """Восстанавливает только собственные исторические поля, не перечитывая текущий склад."""
        return CountSheet.restore(
            **(
                dict(
                    identifier=sheet.id,
                    inventory_count_id=sheet.inventory_count_id,
                    baseline=sheet.baseline,
                    warehouse_id=sheet.warehouse_id,
                    owner_id=sheet.owner_id,
                    status=sheet.status,
                    lines=sheet.lines,
                    created_at=sheet.created_at,
                    updated_at=sheet.updated_at,
                    version=sheet.version,
                )
                | changes
            )
        )

    def test_create_copies_fixed_baseline_fields_with_no_count_default(self) -> None:
        """Факт отсутствует, учётное количество и версия точно скопированы, большой набор не встроен в родителя."""
        line = self.sheet.get_line(self.binding.line_id)
        self.assertEqual(
            (self.sheet.status, self.sheet.version), (CountSheetStatus.DRAFT, 0)
        )
        self.assertEqual(line.baseline_position_snapshot(), self.first)
        self.assertIsNone(line.counted_qty)
        self.assertIsNone(line.counted_at)
        self.assertIsNone(line.discrepancy)
        self.assertEqual(self.sheet.baseline, self.count.baseline)
        self.assertNotIn("sheets", {field.name for field in fields(self.count)})
        self.assertEqual(len(self.sheet.lines), 1)

    def test_known_zero_position_can_be_selected_and_counted(self) -> None:
        """Нулевая учётная позиция может дать излишек без создания новой комбинации измерений."""
        sheet = self.create(bindings=(self.second_binding,))
        result = self.record(sheet, "5", identifier=self.second_binding.line_id)
        self.assertEqual(result.lines[0].expected_qty.value, Decimal(0))
        self.assertEqual(result.lines[0].discrepancy.value, Decimal(5))
        self.assertEqual(self.submit(result).status, CountSheetStatus.SUBMITTED)

    def test_none_is_not_zero_and_zero_can_be_submitted(self) -> None:
        """Непосчитанную строку передать нельзя; явно введённый ноль означает недостачу всего остатка."""
        with self.assertRaises(UncountedCountSheetError):
            self.submit(self.sheet)
        counted = self.record(value="0")
        self.assertEqual(counted.lines[0].counted_qty.value, Decimal(0))
        self.assertEqual(counted.lines[0].discrepancy.value, Decimal(-100))
        self.assertEqual(self.submit(counted).status, CountSheetStatus.SUBMITTED)

    def test_shortage_equality_and_surplus_are_computed_without_stored_delta(
        self,
    ) -> None:
        """Знак вычисляется по факту минус учёт, а производная дельта не дублируется в состоянии."""
        for actual, difference in (("77", "-23"), ("100", "0"), ("105", "5")):
            with self.subTest(actual=actual):
                counted = self.record(value=actual)
                self.assertEqual(
                    counted.lines[0].discrepancy.value, Decimal(difference)
                )
                self.assertNotIn(
                    "discrepancy", {field.name for field in fields(counted.lines[0])}
                )

    def test_discrepancy_is_exact_under_hostile_decimal_context(self) -> None:
        """Большое учётное количество и малая разность не округляются внешним Decimal context."""
        position = replace(
            self.first,
            base_uom=UomCodeVO("KG"),
            on_hand_qty=QuantityVO(Decimal("100000000000000000000.25")),
        )
        line = CountLine.create(identifier=self.binding.line_id, position=position)
        with localcontext() as context:
            context.prec = 2
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            result = line.record_count(
                quantity=QuantityVO(Decimal("100000000000000000000.20")),
                counted_at=self.time,
            )
            self.assertEqual(result.discrepancy.value, Decimal("-0.05"))
            equal = line.record_count(
                quantity=position.on_hand_qty, counted_at=self.time
            )
            self.assertEqual(equal.discrepancy.value, Decimal(0))

    def test_observations_change_only_draft_and_preserve_all_source_values(
        self,
    ) -> None:
        """Повторный пересчёт меняет факт и версию, но не учёт, идентичность или позиции склада."""
        first = self.record()
        later = self.time + timedelta(minutes=5)
        second = self.record(first, "78", counted_at=later, updated_at=later)
        self.assertEqual((first.version, second.version), (1, 2))
        self.assertEqual(second.lines[0].baseline_position_snapshot(), self.first)
        self.assertEqual(second.lines[0].counted_qty.value, Decimal(78))
        self.assertEqual(first.lines[0].counted_qty.value, Decimal(77))
        self.assertIsNone(self.sheet.lines[0].counted_qty)
        self.assertEqual(self.f.position.counting_snapshot(), self.first)
        self.assertEqual(self.count.status, InventoryCountStatus.IN_PROGRESS)

    def test_equal_quantity_and_moment_are_noop_after_validation(self) -> None:
        """Равное наблюдение не обновляет дату; новая дата повторного пересчёта создаёт новую версию."""
        counted = self.record(value="78")
        later = self.time + timedelta(minutes=1)
        self.assertIs(self.record(counted, "78.0", updated_at=later), counted)
        repeated = self.record(counted, "78", counted_at=later, updated_at=later)
        self.assertEqual(repeated.version, 2)
        with self.assertRaises(CountSheetVersionConflictError):
            self.record(counted, "78", expected_version=0)
        with self.assertRaises(QuantityStepError):
            self.record(
                counted,
                "78",
                inventory_item=replace(
                    self.item, quantity_rules=QuantityRulesVO(Decimal(5))
                ),
            )

    def test_current_step_is_checked_on_record_and_again_on_submit(self) -> None:
        """Изменение правил товара между вводом и передачей не приводит к молчаливому округлению."""
        with self.assertRaises(QuantityStepError):
            self.record(value="0.5")
        counted = self.record(value="77")
        with self.assertRaises(QuantityStepError):
            self.submit(
                counted,
                inventory_items=(
                    replace(self.item, quantity_rules=QuantityRulesVO(Decimal(2))),
                ),
            )
        self.assertEqual(counted.status, CountSheetStatus.DRAFT)
        self.assertEqual(counted.lines[0].counted_qty.value, Decimal(77))

    def test_historical_expected_quantity_is_not_revalidated_by_current_step(
        self,
    ) -> None:
        """Старое учётное количество 100.1 KG сохраняется при текущем шаге 0.2 KG, новый факт проверяется."""
        self.first = replace(
            self.first,
            base_uom=UomCodeVO("KG"),
            on_hand_qty=QuantityVO(Decimal("100.1")),
        )
        self.baseline = self.f.build(positions=(self.first,))
        self.count = self.f.start(baseline=self.baseline)
        self.sheet = self.create()
        self.item = replace(
            self.item,
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.2")),
        )
        counted = self.record(value="100.2")
        self.assertEqual(counted.lines[0].discrepancy.value, Decimal("0.1"))
        self.assertEqual(self.submit(counted).status, CountSheetStatus.SUBMITTED)

    def test_serial_actual_count_is_zero_or_one_and_tracking_is_preserved(self) -> None:
        """Конкретный экземпляр нельзя посчитать дважды или перепривязать к режиму без SERIAL."""
        self.first = replace(
            self.first,
            dimensions=replace(
                self.first.dimensions, serial_id=StockSerialIdVO(uuid4())
            ),
            on_hand_qty=QuantityVO(Decimal(1)),
        )
        self.baseline = self.f.build(positions=(self.first,))
        self.count = self.f.start(baseline=self.baseline)
        self.sheet = self.create()
        self.item = replace(self.item, tracking_mode=TrackingMode.SERIAL)
        for actual in ("0", "1"):
            with self.subTest(actual=actual):
                self.assertEqual(
                    self.submit(self.record(value=actual)).status,
                    CountSheetStatus.SUBMITTED,
                )
        with self.assertRaises(InvalidCountLineError):
            self.record(value="2")
        with self.assertRaises(QuantityStepError):
            self.record(value="0.5")
        with self.assertRaises(CountSheetSourceMismatchError):
            self.record(
                inventory_item=replace(self.item, tracking_mode=TrackingMode.NONE)
            )

    def test_lot_and_serial_lines_keep_distinct_source_rows(self) -> None:
        """Строки одного товара в разных партиях и сериях не объединяются по сумме."""
        rows = tuple(
            replace(
                self.first,
                id=StockPositionIdVO(uuid4()),
                dimensions=replace(
                    self.first.dimensions,
                    lot_id=StockLotIdVO(uuid4()),
                    serial_id=StockSerialIdVO(uuid4()),
                ),
                on_hand_qty=QuantityVO(Decimal(1)),
            )
            for _ in range(2)
        )
        self.baseline = self.f.build(positions=rows)
        self.count = self.f.start(baseline=self.baseline)
        bindings = tuple(
            CountSheetLineBindingVO(CountLineIdVO(uuid4()), row.id) for row in rows
        )
        sheet = self.create(bindings=bindings)
        self.item = replace(self.item, tracking_mode=TrackingMode.LOT_AND_SERIAL)
        for binding in bindings:
            sheet = self.record(sheet, "1", identifier=binding.line_id)
        submitted = self.submit(sheet)
        self.assertEqual(len(submitted.lines), 2)
        self.assertEqual(
            {line.dimensions for line in submitted.lines},
            {row.dimensions for row in rows},
        )

    def test_submit_requires_every_selected_line_but_not_every_baseline_position(
        self,
    ) -> None:
        """Ведомость может покрывать часть основания, но внутри неё нельзя пропустить строку."""
        both = self.create(bindings=(self.second_binding, self.binding))
        first = self.record(both)
        with self.assertRaises(UncountedCountSheetError):
            self.submit(first)
        both_counted = self.record(first, "0", identifier=self.second_binding.line_id)
        self.assertEqual(self.submit(both_counted).version, 3)
        self.assertEqual(self.submit(self.record()).status, CountSheetStatus.SUBMITTED)

    def test_submit_rejects_movement_on_unselected_position_and_keeps_observations(
        self,
    ) -> None:
        """Контроль не ограничивается выбранной строкой: изменение второй позиции делает всё основание старым."""
        counted = self.record()
        current = (
            self.first,
            replace(self.second, version=1, on_hand_qty=QuantityVO(Decimal(1))),
        )
        with self.assertRaises(InventoryCountBaselineChangedError):
            self.submit(counted, positions=current)
        self.assertEqual((counted.status, counted.version), (CountSheetStatus.DRAFT, 1))
        self.assertEqual(counted.lines[0].counted_qty.value, Decimal(77))
        with self.assertRaises(InventoryCountBaselineChangedError):
            self.submit(counted, positions=(self.first,))

    def test_new_position_and_round_trip_versions_reject_submission(self) -> None:
        """Новая позиция и движение с возвратом количества не маскируются совпадающими итогами."""
        counted = self.record()
        extra = replace(
            self.second,
            id=StockPositionIdVO(uuid4()),
            dimensions=replace(
                self.second.dimensions, stock_status=StockStatus.DAMAGED
            ),
        )
        for positions in (
            (*self.baseline.positions, extra),
            (replace(self.first, version=9), self.second),
        ):
            with self.subTest(positions=positions):
                with self.assertRaises(InventoryCountBaselineChangedError):
                    self.submit(counted, positions=positions)

    def test_submitted_and_cancelled_are_immutable_and_cancel_preserves_counts(
        self,
    ) -> None:
        """После передачи или отмены нельзя повторно менять, передавать или отменять ведомость."""
        counted = self.record()
        cancelled = counted.cancel(expected_version=1, updated_at=self.time)
        submitted = self.submit(counted)
        self.assertEqual(cancelled.lines, counted.lines)
        self.assertEqual(submitted.lines, counted.lines)
        for sheet in (cancelled, submitted):
            with self.subTest(status=sheet.status):
                with self.assertRaises(CountSheetStatusError):
                    self.record(sheet)
                with self.assertRaises(CountSheetStatusError):
                    self.submit(sheet)
                with self.assertRaises(CountSheetStatusError):
                    sheet.cancel(expected_version=sheet.version, updated_at=self.time)
        self.assertEqual(self.count.version, 2)
        self.assertEqual(self.f.position.on_hand_qty.value, Decimal(100))

    def test_create_requires_running_parent_and_exact_baseline_reference(self) -> None:
        """Подтверждённого плана без запуска недостаточно, ссылка должна вести на точное основание."""
        for status in (
            InventoryCountStatus.DRAFT,
            InventoryCountStatus.CONFIRMED,
            InventoryCountStatus.CANCELLED,
        ):
            with self.subTest(status=status):
                source = replace(
                    self.count.sheet_source_snapshot(), status=status, baseline=None
                )
                with self.assertRaises(InventoryCountStatusError):
                    self.create(inventory_count=source)
        for source in (
            replace(self.count.sheet_source_snapshot(), id=InventoryCountIdVO(uuid4())),
            replace(
                self.count.sheet_source_snapshot(),
                baseline=InventoryCountBaselineRefVO(
                    InventoryCountBaselineIdVO(uuid4()), self.time
                ),
            ),
            replace(
                self.count.sheet_source_snapshot(),
                scope=CountScopeVO(
                    CountType.PARTIAL, tuple(row.id for row in self.f.locations)
                ),
            ),
            replace(
                self.count.sheet_source_snapshot(), warehouse_id=WarehouseIdVO(uuid4())
            ),
            replace(
                self.count.sheet_source_snapshot(), owner_id=StockOwnerIdVO(uuid4())
            ),
        ):
            with self.subTest(source=source):
                with self.assertRaises(CountSheetSourceMismatchError):
                    self.create(inventory_count=source)

    def test_parent_current_version_can_advance_without_changing_baseline(self) -> None:
        """Точная версия старого основания не сравнивается с текущей версией запущенного родителя."""
        source = replace(self.count.sheet_source_snapshot(), version=10)
        self.assertEqual(
            self.create(inventory_count=source).status, CountSheetStatus.DRAFT
        )
        self.assertEqual(
            self.submit(self.record(), inventory_count=source).status,
            CountSheetStatus.SUBMITTED,
        )
        with self.assertRaises(CountSheetSourceMismatchError):
            self.create(
                inventory_count=replace(
                    source, version=self.baseline.inventory_count_version
                )
            )

    def test_submit_rechecks_parent_status_reference_and_saved_sheet_header(
        self,
    ) -> None:
        """После ввода наблюдений повторно проверяются текущий родитель и сохранённые ссылки ведомости."""
        counted = self.record()
        with self.assertRaises(InventoryCountStatusError):
            self.submit(
                counted,
                inventory_count=replace(
                    self.count.sheet_source_snapshot(),
                    status=InventoryCountStatus.CANCELLED,
                    baseline=None,
                ),
            )
        for field, value in (
            ("inventory_count_id", InventoryCountIdVO(uuid4())),
            ("warehouse_id", WarehouseIdVO(uuid4())),
            (
                "baseline",
                InventoryCountBaselineRefVO(
                    InventoryCountBaselineIdVO(uuid4()), self.time
                ),
            ),
        ):
            with self.subTest(field=field):
                forged = self.restore(counted, **{field: value})
                with self.assertRaises(CountSheetSourceMismatchError):
                    self.submit(forged)

    def test_submit_rechecks_all_original_line_fields_against_baseline(self) -> None:
        """Подмена учётного количества, версии, позиции, состояния или единицы не меняет основание."""
        counted = self.record()
        line = counted.lines[0]
        for changed in (
            replace(line, expected_qty=QuantityVO(Decimal(50))),
            replace(line, position_version=8),
            replace(line, position_id=StockPositionIdVO(uuid4())),
            replace(line, base_uom=UomCodeVO("KG")),
            replace(
                line,
                dimensions=replace(line.dimensions, stock_status=StockStatus.DAMAGED),
            ),
        ):
            with self.subTest(changed=changed):
                forged = self.restore(counted, lines=(changed,))
                with self.assertRaises(CountSheetSourceMismatchError):
                    self.submit(forged)

    def test_record_and_submit_require_matching_current_item_unit_and_tracking(
        self,
    ) -> None:
        """Нельзя применить настройки другого товара, переинтерпретировать PCS как KG или заменить режим учёта."""
        for item in (
            replace(self.item, inventory_item_id=InventoryItemIdVO(uuid4())),
            replace(self.item, base_uom=UomCodeVO("KG")),
            replace(self.item, tracking_mode=TrackingMode.LOT),
        ):
            with self.subTest(item=item):
                with self.assertRaises(CountSheetSourceMismatchError):
                    self.record(inventory_item=item)
                with self.assertRaises(CountSheetSourceMismatchError):
                    self.submit(self.record(), inventory_items=(item,))

    def test_submit_requires_exact_unique_current_item_snapshots(self) -> None:
        """Снимки передаются по участвующим товарам, без пропусков, повторов и лишних значений."""
        counted = self.record()
        other = replace(self.item, inventory_item_id=InventoryItemIdVO(uuid4()))
        for items in ((), (self.item, self.item), (self.item, other)):
            with self.subTest(items=items):
                with self.assertRaises(CountSheetSourceMismatchError):
                    self.submit(counted, inventory_items=items)
        for items in ([self.item], (self.f.item,)):
            with self.subTest(items=items):
                with self.assertRaises(InvalidInventoryItemStockSnapshotError):
                    self.submit(counted, inventory_items=items)

    def test_bindings_are_nonempty_typed_unique_and_reference_existing_positions(
        self,
    ) -> None:
        """Фиксированный состав нельзя создать пустым, с повтором строки/позиции или новым измерением вне основания."""
        for bindings in ((), [self.binding], (self.first,)):
            with self.subTest(bindings=bindings):
                with self.assertRaises(InvalidCountSheetLineBindingError):
                    self.create(bindings=bindings)
        for bindings in (
            (self.binding, self.binding),
            (
                self.binding,
                CountSheetLineBindingVO(CountLineIdVO(uuid4()), self.first.id),
            ),
            (
                self.binding,
                CountSheetLineBindingVO(self.binding.line_id, self.second.id),
            ),
        ):
            with self.subTest(bindings=bindings):
                with self.assertRaises(CountSheetLineConflictError):
                    self.create(bindings=bindings)
        with self.assertRaises(CountSheetSourceMismatchError):
            self.create(
                bindings=(
                    CountSheetLineBindingVO(
                        CountLineIdVO(uuid4()), StockPositionIdVO(uuid4())
                    ),
                )
            )
        with self.assertRaises(InvalidCountSheetLineBindingError):
            CountSheetLineBindingVO(self.first.id, self.binding.line_id)

    def test_all_transitions_reject_stale_and_noninteger_versions(self) -> None:
        """Версии проверяются до арифметики и не обходятся повтором равного наблюдения."""
        for action in ("record", "submit", "cancel"):
            with self.subTest(action=action):
                with self.assertRaises(CountSheetVersionConflictError):
                    if action == "record":
                        self.record(expected_version=1)
                    elif action == "submit":
                        self.submit(self.sheet, expected_version=1)
                    else:
                        self.sheet.cancel(expected_version=1, updated_at=self.time)
                for bad in (True, False, -1, 0.0, "0", None):
                    with self.subTest(bad=bad):
                        with self.assertRaises(InvalidCountSheetValueError):
                            if action == "record":
                                self.record(expected_version=bad)
                            elif action == "submit":
                                self.submit(self.sheet, expected_version=bad)
                            else:
                                self.sheet.cancel(
                                    expected_version=bad, updated_at=self.time
                                )
                        with self.assertRaises(InvalidCountSheetValueError):
                            replace(self.sheet, version=bad).cancel(
                                expected_version=0, updated_at=self.time
                            )

    def test_creation_observation_registration_and_parent_time_are_ordered(
        self,
    ) -> None:
        """Нельзя создать ведомость до запуска, посчитать до создания или зарегистрировать наблюдение из будущего."""
        past, future = self.time - timedelta(seconds=1), self.time + timedelta(
            seconds=1
        )
        with self.assertRaises(CountSheetTimeError):
            self.create(created_at=past)
        with self.assertRaises(CountSheetTimeError):
            self.record(counted_at=past)
        with self.assertRaises(CountSheetTimeError):
            self.record(counted_at=future)
        counted = self.record(counted_at=future, updated_at=future)
        with self.assertRaises(CountSheetTimeError):
            self.record(counted, updated_at=future, counted_at=self.time)
        with self.assertRaises(CountSheetTimeError):
            self.submit(counted)
        with self.assertRaises(CountSheetTimeError):
            self.submit(
                self.record(),
                inventory_count=replace(
                    self.count.sheet_source_snapshot(), updated_at=future
                ),
            )

    def test_delayed_observation_of_another_line_can_precede_last_registration(
        self,
    ) -> None:
        """Моменты наблюдения упорядочены для каждой строки, а ввод другой строки может быть задержан."""
        sheet = self.create(bindings=(self.binding, self.second_binding))
        first_time = self.time + timedelta(minutes=10)
        second_time = self.time + timedelta(minutes=5)
        sheet = self.record(sheet, counted_at=first_time, updated_at=first_time)
        sheet = self.record(
            sheet,
            "0",
            identifier=self.second_binding.line_id,
            counted_at=second_time,
            updated_at=first_time + timedelta(minutes=1),
        )
        self.assertEqual(
            sheet.get_line(self.second_binding.line_id).counted_at, second_time
        )
        self.assertEqual(
            self.submit(sheet, updated_at=sheet.updated_at).status,
            CountSheetStatus.SUBMITTED,
        )

    def test_aware_times_normalize_to_utc_and_naive_times_fail(self) -> None:
        """Моменты в другом поясе сохраняют смысл, наивные даты не принимаются."""
        local = self.time.astimezone(timezone(timedelta(hours=2)))
        sheet = self.create(created_at=local)
        counted = self.record(sheet, counted_at=local, updated_at=local)
        self.assertIs(counted.updated_at.tzinfo, UTC)
        self.assertIs(counted.lines[0].counted_at.tzinfo, UTC)
        for bad in (None, "now", self.time.replace(tzinfo=None)):
            with self.subTest(bad=bad):
                with self.assertRaises(CountSheetTimeError):
                    self.create(created_at=bad)
                with self.assertRaises(CountSheetTimeError):
                    self.record(counted_at=bad)
                with self.assertRaises(CountSheetTimeError):
                    self.record(updated_at=bad)

    def test_restore_preserves_own_history_without_current_parent_or_items(
        self,
    ) -> None:
        """Черновик, отменённая и переданная история восстанавливаются без загрузки основания."""
        counted = self.record()
        for sheet in (
            self.sheet,
            counted,
            counted.cancel(expected_version=1, updated_at=self.time),
            self.submit(counted),
        ):
            with self.subTest(status=sheet.status):
                self.assertEqual(self.restore(sheet), sheet)
        with self.assertRaises(UncountedCountSheetError):
            self.restore(self.sheet, status=CountSheetStatus.SUBMITTED)

    def test_restore_rejects_invalid_own_fields_duplicate_rows_and_foreign_owner(
        self,
    ) -> None:
        """Восстановление проверяет собственные инварианты, хотя не доказывает актуальность внешних данных."""
        for field, value in (
            ("identifier", self.count.id),
            ("inventory_count_id", self.sheet.id),
            ("baseline", None),
            ("status", "DRAFT"),
            ("lines", ()),
            ("lines", list(self.sheet.lines)),
            ("version", True),
            ("version", -1),
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidCountSheetValueError):
                    self.restore(self.sheet, **{field: value})
        line = self.sheet.lines[0]
        for lines in (
            (line, line),
            (line, replace(line, id=CountLineIdVO(uuid4()))),
            (
                line,
                replace(
                    line,
                    id=CountLineIdVO(uuid4()),
                    position_id=StockPositionIdVO(uuid4()),
                ),
            ),
        ):
            with self.assertRaises(CountSheetLineConflictError):
                self.restore(self.sheet, lines=lines)
        with self.assertRaises(InvalidCountSheetValueError):
            self.restore(self.sheet, owner_id=StockOwnerIdVO(uuid4()))
        with self.assertRaises(CountSheetTimeError):
            self.restore(self.sheet, created_at=self.time - timedelta(seconds=1))

    def test_line_restore_requires_paired_observation_and_valid_position_version(
        self,
    ) -> None:
        """Локальные поля факта заполняются вместе, исходная версия остаётся строго целой."""
        line = self.sheet.lines[0]
        for changed in (
            replace(line, counted_qty=QuantityVO(Decimal(0))),
            replace(line, counted_at=self.time),
        ):
            with self.assertRaises(InvalidCountLineError):
                changed.ensure_valid()
        with self.assertRaises(InvalidStockPositionCountingSnapshotError):
            replace(line, position_version=True).ensure_valid()
        restored = CountLine.restore(
            identifier=line.id,
            origin=line.origin,
            position_id=line.position_id,
            dimensions=line.dimensions,
            base_uom=line.base_uom,
            expected_qty=line.expected_qty,
            position_version=line.position_version,
            counted_qty=QuantityVO(Decimal(0)),
            counted_at=self.time.astimezone(timezone(timedelta(hours=2))),
        )
        self.assertIs(restored.counted_at.tzinfo, UTC)
        self.assertEqual(restored.discrepancy.value, Decimal(-100))

    def test_runtime_snapshot_and_policy_contracts_reject_wrong_objects(self) -> None:
        """Сырые корни, снимок другого назначения и нетипизированные входы не проходят публичные политики."""
        with self.assertRaises(InvalidInventoryCountSheetSourceError):
            self.create(inventory_count=self.count)
        with self.assertRaises(InvalidInventoryCountBaselineError):
            self.create(baseline=object())
        with self.assertRaises(InvalidInventoryItemStockSnapshotError):
            self.record(inventory_item=self.f.item)
        with self.assertRaises(InvalidQuantityError):
            self.record(counted_qty=Decimal(1))
        with self.assertRaises(InvalidCountLineError):
            CountSheetLinePolicy.ensure_compatible(
                line=self.first,
                inventory_item=self.item,
                quantity=QuantityVO(Decimal(1)),
            )
        with self.assertRaises(InvalidInventoryCountSheetSourceError):
            self.create(
                inventory_count=replace(
                    self.count.sheet_source_snapshot(), version=True
                )
            )
        with self.assertRaises(InvalidInventoryCountSheetSourceError):
            self.create(
                inventory_count=replace(
                    self.count.sheet_source_snapshot(), baseline=None
                )
            )
        with self.assertRaises(InvalidCountSheetValueError):
            CountSheetSourcePolicy.ensure_sheet_source(
                inventory_count_id=self.sheet.inventory_count_id,
                warehouse_id=self.sheet.warehouse_id,
                owner_id=self.sheet.owner_id,
                baseline_ref=self.sheet.baseline,
                lines=(),
                inventory_count=self.count.sheet_source_snapshot(),
                baseline=self.baseline,
            )

    def test_unknown_line_cannot_be_recorded_and_objects_are_immutable(self) -> None:
        """Нельзя записать факт в чужую строку или изменить поля присваиванием."""
        with self.assertRaises(CountSheetLineNotFoundError):
            self.record(identifier=CountLineIdVO(uuid4()))
        with self.assertRaises(InvalidCountLineError):
            self.record(identifier=self.first.id)
        with self.assertRaises(FrozenInstanceError):
            self.sheet.status = CountSheetStatus.SUBMITTED
        with self.assertRaises(FrozenInstanceError):
            self.sheet.lines[0].counted_qty = QuantityVO(Decimal(1))


if __name__ == "__main__":
    unittest.main()
