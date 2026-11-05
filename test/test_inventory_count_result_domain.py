"""Сводный результат: полное покрытие, межведомостные конфликты, SERIAL, отзыв и COUNTED без проведения."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, timedelta, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_count_sheet_domain as sheet_fixture
from src.modules.inventory.domain.count_sheet.aggregate import CountSheet
from src.modules.inventory.domain.count_sheet.error import (
    InvalidCountSheetReconciliationSnapshotError,
    InvalidCountSheetValueError,
    CountSheetStatusError,
    CountSheetTimeError,
    CountSheetSourceMismatchError,
    CountSheetVersionConflictError,
)
from src.modules.inventory.domain.count_sheet.value_object.identifier import (
    CountSheetIdVO,
)
from src.modules.inventory.domain.count_sheet.value_object.line_id import CountLineIdVO
from src.modules.inventory.domain.count_sheet.value_object.status import (
    CountSheetStatus,
)
from src.modules.inventory.domain.error import QuantityStepError
from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountResultError,
    InvalidInventoryCountValueError,
    InventoryCountBaselineChangedError,
    InventoryCountCoverageError,
    InventoryCountResultConflictError,
    InventoryCountResultMismatchError,
    InventoryCountSerialConflictError,
    InventoryCountSheetsNotReadyError,
    InventoryCountStatusError,
    InventoryCountTimeError,
    InventoryCountVersionConflictError,
)
from src.modules.inventory.domain.inventory_count.aggregate import InventoryCount
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.inventory_count.value_object.result_id import (
    InventoryCountResultIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.result_ref import (
    InventoryCountResultRefVO,
)
from src.modules.inventory.domain.inventory_count.value_object.status import (
    InventoryCountStatus,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.policy.inventory_count_result import (
    InventoryCountResultPolicy,
)
from src.modules.inventory.domain.inventory_count.result_snapshot import (
    InventoryCountResultSnapshot,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class InventoryCountResultDomainTests(unittest.TestCase):
    """Проверяет отдельный immutable результат и его регистрацию по свежему полному набору источников."""

    def setUp(self) -> None:
        """Готовит две переданные ведомости: 100 → 77 и известная нулевая позиция 0 → 0."""
        self.f = sheet_fixture.InventoryCountSheetDomainTests()
        self.f.setUp()
        self.time = self.f.time
        self.count, self.baseline, self.item = (
            self.f.count,
            self.f.baseline,
            self.f.item,
        )
        self.first = self.f.submit(self.f.record())
        second = self.f.create(bindings=(self.f.second_binding,))
        self.second = self.f.submit(
            self.f.record(second, "0", identifier=self.f.second_binding.line_id)
        )
        self.sheets = (self.first, self.second)
        self.identifier = InventoryCountResultIdVO(uuid4())

    def context(self) -> dict[str, object]:
        """Передаёт полный текущий набор источников и позиций, без фильтра статусов ведомостей."""
        return dict(
            inventory_count=self.count.sheet_source_snapshot(),
            baseline=self.baseline,
            sheets=tuple(sheet.reconciliation_snapshot() for sheet in self.sheets),
            inventory_items=(self.item,),
            locations=self.baseline.locations,
            positions=self.baseline.positions,
        )

    def build(self, **changes: object) -> InventoryCountResultSnapshot:
        """Собирает результат по текущим переданным снимкам без изменения источников."""
        return InventoryCountResultPolicy.build_result(
            **(
                dict(identifier=self.identifier, prepared_at=self.time)
                | self.context()
                | changes
            )
        )

    def register(
        self, result: InventoryCountResultSnapshot, **changes: object
    ) -> InventoryCount:
        """Повторно передаёт текущие ведомости и физическое состояние при регистрации ссылки в корне."""
        context = self.context()
        context.pop("inventory_count")
        return self.count.register_result(
            result,
            **(
                dict(expected_version=self.count.version, updated_at=self.time)
                | context
                | changes
            ),
        )

    def withdraw(self, sheet: CountSheet, **changes: object) -> CountSheet:
        """Отзывает переданную ведомость до COUNTED, сохраняя историю наблюдений."""
        return sheet.withdraw(
            **(
                dict(
                    inventory_count=self.count.sheet_source_snapshot(),
                    expected_version=sheet.version,
                    updated_at=self.time,
                )
                | changes
            )
        )

    def found(
        self,
        *,
        quantity: str = "5",
        item: InventoryItemStockSnapshot | None = None,
        serial: StockSerialSnapshot | None = None,
        dimensions: StockDimensionsVO | None = None,
    ) -> CountSheet:
        """Готовит независимую переданную FOUND-ведомость на новые измерения внутри основания."""
        current_item = self.item if item is None else item
        target = (
            dimensions
            if dimensions is not None
            else replace(
                self.baseline.positions[0].dimensions,
                inventory_item_id=current_item.inventory_item_id,
                location_id=self.f.f.other_location.id,
                stock_status=StockStatus.DAMAGED,
                serial_id=None if serial is None else serial.id,
            )
        )
        location = next(
            row for row in self.baseline.locations if row.id == target.location_id
        )
        identifier = CountLineIdVO(uuid4())
        draft = CountSheet.create_with_found_line(
            identifier=CountSheetIdVO(uuid4()),
            line_id=identifier,
            inventory_count=self.count.sheet_source_snapshot(),
            baseline=self.baseline,
            dimensions=target,
            inventory_item=current_item,
            warehouse=self.f.f.warehouse,
            location=location,
            serial=serial,
            created_at=self.time,
        )
        counted = draft.record_count(
            identifier,
            counted_qty=QuantityVO(Decimal(quantity)),
            counted_at=self.time,
            inventory_item=current_item,
            expected_version=0,
            updated_at=self.time,
        )
        return counted.submit(
            expected_version=1,
            updated_at=self.time,
            inventory_count=self.count.sheet_source_snapshot(),
            baseline=self.baseline,
            inventory_items=(current_item,),
            locations=self.baseline.locations,
            positions=self.baseline.positions,
            warehouse=self.f.f.warehouse,
            serials=() if serial is None else (serial,),
        )

    def serial_sources(self, actual: str) -> StockSerialSnapshot:
        """Заменяет основу одной серийной позицией и её переданной ведомостью."""
        self.item = replace(self.item, tracking_mode=TrackingMode.SERIAL)
        serial = StockSerialSnapshot(
            StockSerialIdVO(uuid4()), self.item.inventory_item_id, None
        )
        position = replace(
            self.f.first,
            dimensions=replace(self.f.first.dimensions, serial_id=serial.id),
            on_hand_qty=QuantityVO(Decimal(1)),
        )
        self.baseline = self.f.f.build(positions=(position,))
        self.count = self.f.f.start(baseline=self.baseline)
        self.f.baseline, self.f.count, self.f.item = (
            self.baseline,
            self.count,
            self.item,
        )
        self.first = self.f.submit(self.f.record(self.f.create(), actual))
        self.sheets = (self.first,)
        return serial

    def test_build_and_register_keep_zero_rows_and_only_reference_in_root(self) -> None:
        """Обе позиции покрыты, нулевая дельта сохранена, в корне только ID и момент результата."""
        result = self.build()
        counted = self.register(result)
        self.assertEqual(len(result.lines), 2)
        self.assertEqual(
            {row.discrepancy.value for row in result.lines}, {Decimal(-23), Decimal(0)}
        )
        self.assertEqual(result.inventory_count_version, self.count.version)
        self.assertEqual(
            (counted.status, counted.version),
            (InventoryCountStatus.COUNTED, self.count.version + 1),
        )
        self.assertEqual(
            counted.result, InventoryCountResultRefVO(result.id, result.prepared_at)
        )
        self.assertNotIn("lines", {field.name for field in fields(counted)})
        self.assertNotIn("sheet_revisions", {field.name for field in fields(counted)})
        self.assertEqual(self.count.status, InventoryCountStatus.IN_PROGRESS)
        self.assertIsNone(self.count.result)
        self.assertEqual(self.f.f.position.on_hand_qty.value, Decimal(100))

    def test_input_order_does_not_change_result(self) -> None:
        """Порядок чтения ведомостей, строк и позиций не влияет на канонический результат."""
        expected = self.build()
        actual = self.build(
            sheets=tuple(reversed(self.context()["sheets"])),
            positions=tuple(reversed(self.baseline.positions)),
            locations=tuple(reversed(self.baseline.locations)),
        )
        self.assertEqual(actual, expected)

    def test_full_coverage_includes_known_zero_positions(self) -> None:
        """Пропуск нулевой позиции также означает неполный пересчёт основания."""
        with self.assertRaises(InventoryCountCoverageError):
            self.build(sheets=(self.first.reconciliation_snapshot(),))
        with self.assertRaises(InventoryCountCoverageError):
            self.build(sheets=())

    def test_draft_is_not_silently_filtered_even_when_coverage_is_complete(
        self,
    ) -> None:
        """Незавершённый черновик нельзя скрыть за готовыми ведомостями на те же позиции."""
        with self.assertRaises(InventoryCountSheetsNotReadyError):
            self.build(
                sheets=(
                    *self.context()["sheets"],
                    self.f.create().reconciliation_snapshot(),
                )
            )

    def test_duplicate_sheet_and_multiple_versions_are_rejected(self) -> None:
        """Одна ведомость передаётся один раз, политика не выбирает свежую ревизию из дубликатов."""
        snapshot = self.first.reconciliation_snapshot()
        for duplicate in (snapshot, replace(snapshot, version=snapshot.version + 1)):
            with self.subTest(duplicate=duplicate.version):
                with self.assertRaises(InventoryCountResultConflictError):
                    self.build(sheets=(*self.context()["sheets"], duplicate))

    def test_same_position_in_two_submitted_sheets_is_conflict_even_if_counts_match(
        self,
    ) -> None:
        """Равные наблюдения не разрешают суммировать или автоматически выбирать одну ведомость."""
        duplicate = self.f.submit(self.f.record(self.f.create()))
        with self.assertRaises(InventoryCountResultConflictError):
            self.build(
                sheets=(*self.context()["sheets"], duplicate.reconciliation_snapshot())
            )

    def test_same_line_identifier_in_distinct_sheets_has_unambiguous_provenance(
        self,
    ) -> None:
        """Идентичность источника составная: ведомость и её дочерняя строка, без нового глобального ограничения ID строк."""
        changed_line = replace(self.second.lines[0], id=self.first.lines[0].id)
        second = self.f.restore(self.second, lines=(changed_line,))
        result = self.build(
            sheets=(
                self.first.reconciliation_snapshot(),
                second.reconciliation_snapshot(),
            )
        )
        self.assertEqual(len(result.lines), 2)
        self.assertEqual(
            len({(row.sheet_id, row.observation.id) for row in result.lines}), 2
        )

    def test_found_rows_are_included_but_cross_sheet_found_duplicates_are_rejected(
        self,
    ) -> None:
        """Найденный запас входит в результат отдельно, но одинаковые измерения разных ведомостей конфликтуют."""
        first, duplicate = self.found(), self.found()
        result = self.build(
            sheets=(*self.context()["sheets"], first.reconciliation_snapshot()),
            warehouse=self.f.f.warehouse,
        )
        self.assertEqual(len(result.lines), 3)
        self.assertIn(Decimal(5), {row.discrepancy.value for row in result.lines})
        with self.assertRaises(InventoryCountResultConflictError):
            self.build(
                sheets=(
                    *self.context()["sheets"],
                    first.reconciliation_snapshot(),
                    duplicate.reconciliation_snapshot(),
                ),
                warehouse=self.f.f.warehouse,
            )

    def test_withdraw_preserves_observations_and_records_revision(self) -> None:
        """Отзыв исключает ведомость из расчёта, сохраняя её неизменные наблюдения и новую версию."""
        withdrawn = self.withdraw(self.first)
        self.assertEqual(
            (withdrawn.status, withdrawn.version),
            (CountSheetStatus.WITHDRAWN, self.first.version + 1),
        )
        self.assertEqual(withdrawn.lines, self.first.lines)
        self.assertEqual(self.first.status, CountSheetStatus.SUBMITTED)
        self.assertEqual(self.f.restore(withdrawn), withdrawn)
        replacement = self.f.submit(self.f.record(self.f.create(), "75"))
        self.sheets = (withdrawn, replacement, self.second)
        result = self.build()
        self.assertEqual(len(result.sheet_revisions), 3)
        self.assertNotIn(withdrawn.id, {row.sheet_id for row in result.lines})
        self.assertIn(Decimal(-25), {row.discrepancy.value for row in result.lines})
        self.assertEqual(self.register(result).status, InventoryCountStatus.COUNTED)

    def test_cancelled_and_withdrawn_do_not_cover_positions(self) -> None:
        """Отменённая или отозванная ведомость не заменяет результат пересчёта позиции."""
        cancelled = self.f.create().cancel(expected_version=0, updated_at=self.time)
        for excluded in (cancelled, self.withdraw(self.first)):
            with self.subTest(status=excluded.status):
                with self.assertRaises(InventoryCountCoverageError):
                    self.build(
                        sheets=(
                            excluded.reconciliation_snapshot(),
                            self.second.reconciliation_snapshot(),
                        )
                    )
        result = self.build(
            sheets=(*self.context()["sheets"], cancelled.reconciliation_snapshot())
        )
        self.assertEqual(len(result.lines), 2)
        self.assertEqual(len(result.sheet_revisions), 3)

    def test_withdraw_requires_submitted_and_does_not_reopen_rows(self) -> None:
        """Отзыв — отдельный окончательный переход, отмена черновика сохраняет прежнее поведение."""
        withdrawn = self.withdraw(self.first)
        cancelled = self.f.create().cancel(expected_version=0, updated_at=self.time)
        for sheet in (self.f.create(), withdrawn, cancelled):
            with self.subTest(status=sheet.status):
                with self.assertRaises(CountSheetStatusError):
                    self.withdraw(sheet)
        with self.assertRaises(CountSheetStatusError):
            self.f.record(withdrawn)
        with self.assertRaises(CountSheetStatusError):
            withdrawn.cancel(expected_version=withdrawn.version, updated_at=self.time)
        with self.assertRaises(InvalidCountSheetReconciliationSnapshotError):
            replace(
                withdrawn.reconciliation_snapshot(),
                lines=self.f.create().reconciliation_snapshot().lines,
            ).ensure_valid()

    def test_withdraw_checks_version_current_parent_and_time(self) -> None:
        """Отзыв не требует свежести физического основания, но требует правильного исполняемого родителя."""
        with self.assertRaises(CountSheetVersionConflictError):
            self.withdraw(self.first, expected_version=0)
        for bad in (True, -1, "2", None):
            with self.subTest(version=bad):
                with self.assertRaises(InvalidCountSheetValueError):
                    self.withdraw(self.first, expected_version=bad)
        with self.assertRaises(CountSheetTimeError):
            self.withdraw(self.first, updated_at=self.time - timedelta(seconds=1))
        with self.assertRaises(CountSheetSourceMismatchError):
            self.withdraw(
                self.first,
                inventory_count=replace(
                    self.count.sheet_source_snapshot(),
                    warehouse_id=WarehouseIdVO(uuid4()),
                ),
            )
        parent = replace(
            self.count.sheet_source_snapshot(),
            status=InventoryCountStatus.CANCELLED,
            baseline=None,
        )
        with self.assertRaises(InventoryCountStatusError):
            self.withdraw(self.first, inventory_count=parent)

    def test_serial_can_move_between_observed_addresses_if_only_one_positive(
        self,
    ) -> None:
        """Ноль на старом месте и единица на найденном новом месте — согласованный результат, дельты не объединяются."""
        serial = self.serial_sources("0")
        self.sheets += (self.found(quantity="1", serial=serial),)
        result = self.build(warehouse=self.f.f.warehouse, serials=(serial,))
        self.assertEqual(
            {row.discrepancy.value for row in result.lines}, {Decimal(-1), Decimal(1)}
        )
        self.assertEqual(
            self.register(
                result, warehouse=self.f.f.warehouse, serials=(serial,)
            ).status,
            InventoryCountStatus.COUNTED,
        )

    def test_serial_cannot_be_positive_in_two_positions_even_when_one_delta_is_zero(
        self,
    ) -> None:
        """Сравниваются фактические количества: нулевая дельта в старом адресе не скрывает второй экземпляр."""
        serial = self.serial_sources("1")
        self.sheets += (self.found(quantity="1", serial=serial),)
        with self.assertRaises(InventoryCountSerialConflictError):
            self.build(warehouse=self.f.f.warehouse, serials=(serial,))

    def test_serial_identity_must_match_even_for_zero_observation(self) -> None:
        """Один UUID SERIAL не может одновременно обозначать разные товары в наблюдениях одной области."""
        serial = self.serial_sources("0")
        other_item = replace(self.item, inventory_item_id=InventoryItemIdVO(uuid4()))
        other_serial = replace(serial, inventory_item_id=other_item.inventory_item_id)
        other = self.found(quantity="1", item=other_item, serial=other_serial)
        with self.assertRaises(InventoryCountSerialConflictError):
            self.build(
                sheets=(*self.context()["sheets"], other.reconciliation_snapshot()),
                inventory_items=(self.item, other_item),
                warehouse=self.f.f.warehouse,
                serials=(other_serial,),
            )

    def test_stock_changed_after_submission_or_preparation_rejects_result(self) -> None:
        """Старое основание не используется ни при сборке, ни при регистрации уже собранного результата."""
        result = self.build()
        changed = (
            replace(self.baseline.positions[0], version=8),
            self.baseline.positions[1],
        )
        with self.assertRaises(InventoryCountBaselineChangedError):
            self.build(positions=changed)
        with self.assertRaises(InventoryCountBaselineChangedError):
            self.register(result, positions=changed)
        self.assertIsNone(self.count.result)

    def test_withdrawal_after_preparation_is_rechecked_during_registration(
        self,
    ) -> None:
        """Версия родителя не меняется при отзыве ведомости, поэтому её текущая ревизия проверяется отдельно."""
        result = self.build()
        self.sheets = (self.withdraw(self.first), self.second)
        with self.assertRaises(InventoryCountCoverageError):
            self.register(result)
        self.assertEqual(self.count.version, result.inventory_count_version)
        self.assertIsNone(self.count.result)

    def test_changed_sheet_version_or_roster_rejects_prepared_result(self) -> None:
        """Даже отменённая новая ведомость меняет состав источников, а новая ревизия — точное происхождение результата."""
        result = self.build()
        snapshots = self.context()["sheets"]
        changed = replace(snapshots[0], version=snapshots[0].version + 1)
        with self.assertRaises(InventoryCountResultMismatchError):
            self.register(result, sheets=(changed, snapshots[1]))
        cancelled = self.f.create().cancel(expected_version=0, updated_at=self.time)
        with self.assertRaises(InventoryCountResultMismatchError):
            self.register(
                result, sheets=(*snapshots, cancelled.reconciliation_snapshot())
            )

    def test_empty_baseline_can_be_explicitly_recorded_without_fake_rows(self) -> None:
        """Пустой учётный набор не требует фиктивной позиции, ведомости или нулевой проводки."""
        self.baseline = self.f.f.build(positions=())
        self.count = self.f.f.start(baseline=self.baseline)
        self.sheets = ()
        result = self.build(inventory_items=())
        self.assertEqual((result.lines, result.sheet_revisions), ((), ()))
        self.assertEqual(
            self.register(result, inventory_items=()).status,
            InventoryCountStatus.COUNTED,
        )

    def test_empty_baseline_can_have_found_only_result(self) -> None:
        """Пустое основание допускает найденный запас без добавления позиции в исходный снимок."""
        self.baseline = self.f.f.build(positions=())
        self.count = self.f.f.start(baseline=self.baseline)
        dimensions = replace(self.f.first.dimensions, stock_status=StockStatus.DAMAGED)
        self.sheets = (self.found(dimensions=dimensions),)
        result = self.build(warehouse=self.f.f.warehouse)
        self.assertEqual(result.lines[0].discrepancy.value, Decimal(5))
        self.assertIsNone(result.lines[0].observation.position_id)

    def test_all_zero_discrepancies_still_form_counted_result(self) -> None:
        """Нулевые расхождения подтверждают покрытие, а не создают нулевой StockPosting."""
        self.first = self.f.submit(self.f.record(self.f.create(), "100"))
        self.sheets = (self.first, self.second)
        result = self.build()
        self.assertTrue(all(row.discrepancy.value.is_zero() for row in result.lines))
        self.assertEqual(self.register(result).status, InventoryCountStatus.COUNTED)

    def test_quantity_rules_rechecked_and_discrepancy_remains_exact(self) -> None:
        """Правила могут измениться после передачи, а вычисление разности не зависит от внешней точности."""
        with self.assertRaises(QuantityStepError):
            self.build(
                inventory_items=(
                    replace(self.item, quantity_rules=QuantityRulesVO(Decimal(2))),
                )
            )
        result = self.build()
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            self.assertEqual(
                {row.discrepancy.value for row in result.lines},
                {Decimal(-23), Decimal(0)},
            )

    def test_times_normalize_and_preparation_covers_parent_and_all_sheets(self) -> None:
        """Момент подготовки не заменяет моменты наблюдения и не может предшествовать источникам."""
        local = self.time.astimezone(timezone(timedelta(hours=2)))
        result = self.build(prepared_at=local)
        self.assertIs(result.prepared_at.tzinfo, UTC)
        self.assertIs(
            InventoryCountResultRefVO(result.id, local).prepared_at.tzinfo, UTC
        )
        with self.assertRaises(InventoryCountTimeError):
            self.build(prepared_at=self.time - timedelta(seconds=1))
        later = self.time + timedelta(seconds=1)
        with self.assertRaises(InventoryCountTimeError):
            self.build(
                sheets=(
                    replace(self.first.reconciliation_snapshot(), updated_at=later),
                    self.second.reconciliation_snapshot(),
                )
            )
        future = self.build(prepared_at=later)
        with self.assertRaises(InventoryCountTimeError):
            self.register(future)
        self.assertEqual(
            self.register(future, updated_at=later).result.prepared_at, later
        )

    def test_registration_requires_current_integer_version_and_exact_result_version(
        self,
    ) -> None:
        """Ожидаемая версия проверяется до вычислений, источник результата не переносится на следующую версию корня."""
        result = self.build()
        for version in (True, -1, "2", None):
            with self.subTest(version=version):
                with self.assertRaises(InvalidInventoryCountValueError):
                    self.register(result, expected_version=version)
        with self.assertRaises(InventoryCountVersionConflictError):
            self.register(result, expected_version=0)
        with self.assertRaises(InventoryCountVersionConflictError):
            self.register(
                replace(result, inventory_count_version=self.count.version - 1)
            )

    def test_counted_blocks_repeated_result_new_sheets_submission_and_withdrawal(
        self,
    ) -> None:
        """COUNTED закрывает набор наблюдений, оставаясь отдельным состоянием от проведения корректировок."""
        result = self.build()
        counted = self.register(result)
        with self.assertRaises(InventoryCountStatusError):
            counted.register_result(
                result,
                expected_version=counted.version,
                updated_at=self.time,
                baseline=self.baseline,
                sheets=self.context()["sheets"],
                inventory_items=(self.item,),
                locations=self.baseline.locations,
                positions=self.baseline.positions,
            )
        source = counted.sheet_source_snapshot()
        with self.assertRaises(InventoryCountStatusError):
            self.f.create(inventory_count=source)
        with self.assertRaises(InventoryCountStatusError):
            self.f.submit(self.f.record(), inventory_count=source)
        with self.assertRaises(InventoryCountStatusError):
            self.withdraw(self.first, inventory_count=source)

    def test_restore_enforces_counted_result_reference_and_chronology(self) -> None:
        """История COUNTED восстанавливается без большого результата, но требует ссылку и прежнее основание."""
        counted = self.register(self.build())
        self.assertEqual(self.f.f.restore(counted), counted)
        for changes in (
            dict(result=None),
            dict(baseline=None),
            dict(status=InventoryCountStatus.IN_PROGRESS),
            dict(result=self.build()),
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(InvalidInventoryCountValueError):
                    self.f.f.restore(counted, **changes)
        for moment in (
            self.time - timedelta(seconds=1),
            self.time + timedelta(seconds=1),
        ):
            with self.assertRaises(InventoryCountTimeError):
                self.f.f.restore(
                    counted, result=InventoryCountResultRefVO(counted.result.id, moment)
                )

    def test_ignored_sheets_still_require_correct_header_and_valid_snapshot(
        self,
    ) -> None:
        """Чужая отменённая ведомость не прячется за тем, что её строки не участвуют в результате."""
        cancelled = (
            self.f.create()
            .cancel(expected_version=0, updated_at=self.time)
            .reconciliation_snapshot()
        )
        with self.assertRaises(InventoryCountResultMismatchError):
            self.build(
                sheets=(
                    *self.context()["sheets"],
                    replace(cancelled, warehouse_id=WarehouseIdVO(uuid4())),
                )
            )
        with self.assertRaises(InvalidCountSheetReconciliationSnapshotError):
            self.build(sheets=(*self.context()["sheets"], replace(cancelled, lines=())))

    def test_snapshot_and_result_public_contracts_reject_wrong_types(self) -> None:
        """Корни, нетипизированные строки и bool-версии не заменяют специализированные снимки."""
        for sheets in ([self.first.reconciliation_snapshot()], (self.first,)):
            with self.subTest(sheets=sheets):
                with self.assertRaises(InvalidInventoryCountResultError):
                    self.build(sheets=sheets)
        with self.assertRaises(InvalidCountSheetReconciliationSnapshotError):
            replace(
                self.first.reconciliation_snapshot(), lines=self.first.lines
            ).ensure_valid()
        result = self.build()
        for field, value in (
            ("inventory_count_version", True),
            ("id", self.count.id),
            ("sheet_revisions", []),
            ("lines", []),
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidInventoryCountResultError):
                    replace(result, **{field: value}).ensure_valid()
        with self.assertRaises(InvalidInventoryCountResultError):
            self.register(self.count)

    def test_changed_original_expected_fields_and_result_omission_cannot_be_registered(
        self,
    ) -> None:
        """Неизменность источников проверяется повторно, а не предполагается из номинального типа результата."""
        result = self.build()
        first = self.first.reconciliation_snapshot()
        altered = replace(first.lines[0], expected_qty=QuantityVO(Decimal(50)))
        with self.assertRaises(InventoryCountResultMismatchError):
            self.build(
                sheets=(
                    replace(first, lines=(altered,)),
                    self.second.reconciliation_snapshot(),
                )
            )
        keep = next(row for row in result.lines if row.sheet_id == self.first.id)
        truncated = replace(
            result,
            lines=(keep,),
            sheet_revisions=tuple(
                rev for rev in result.sheet_revisions if rev.id == self.first.id
            ),
        )
        truncated.ensure_valid()
        with self.assertRaises(InventoryCountResultMismatchError):
            self.register(truncated)

    def test_result_and_sources_are_immutable(self) -> None:
        """Сводный набор и ссылки не меняются при последующих локальных операциях или присваивании."""
        result = self.build()
        with self.assertRaises(FrozenInstanceError):
            result.lines = ()
        with self.assertRaises(FrozenInstanceError):
            result.sheet_revisions[0].version = 99
        with self.assertRaises(FrozenInstanceError):
            result.lines[0].observation.counted_qty = QuantityVO(Decimal(0))


if __name__ == "__main__":
    unittest.main()
