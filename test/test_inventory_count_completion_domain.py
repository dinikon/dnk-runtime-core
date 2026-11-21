"""Закрытие инвентаризации по историческому применению либо нулевому результату без повторного чтения остатков."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from test import test_inventory_adjustment_application_domain as application_fixture
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.inventory_count.aggregate import InventoryCount
from src.modules.inventory.domain.inventory_count.result_snapshot import (
    InventoryCountResultSnapshot,
)
from src.modules.inventory.domain.stock_posting.adjustment_application_snapshot import (
    StockAdjustmentApplicationSnapshot,
)
from src.modules.inventory.domain.inventory_count.error import (
    InventoryCountCompletionError,
)
from src.modules.inventory.domain.inventory_count.value_object.completion import (
    InventoryCountCompletionVO,
)
from src.modules.inventory.domain.inventory_count.value_object.identifier import (
    InventoryCountIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.result_id import (
    InventoryCountResultIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.status import (
    InventoryCountStatus,
)
from src.modules.inventory.domain.policy.count_sheet_source import (
    CountSheetSourcePolicy,
)
from src.modules.inventory.domain.policy.stock_adjustment_application import (
    StockAdjustmentApplicationPolicy,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.ledger_entry_id import (
    StockLedgerEntryIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class InventoryCountCompletionDomainTests(unittest.TestCase):
    """Проверяет завершение без новых AR, I/O и подмены результата применения планируемыми записями."""

    def setUp(self) -> None:
        """Готовит применённые −23/+5 и завершённый документ, сохраняя COUNTED-родителя."""
        self.f = application_fixture.AdjustmentApplicationDomainTests()
        self.f.setUp()
        self.prepare_evidence()

    def prepare_evidence(self) -> None:
        """Формирует согласованные исторические факты через публичные методы предыдущего среза."""
        self.execution = self.f.execute()
        self.posting = self.f.post(self.execution)
        changed = self.f.apply(self.posting, self.execution)
        affected = {entry.position_id for entry in self.posting.entries}
        self.positions_after = tuple(
            position.counting_snapshot()
            for position in changed
            if position.id in affected
        )
        self.document = self.f.document.register_adjustment_execution(
            self.execution.adjustment_snapshot(), updated_at=self.f.f.time
        )
        self.application = self.build_application()
        self.count, self.result = self.f.f.count, self.f.f.result
        self.time = self.f.f.time + timedelta(seconds=1)

    def build_application(
        self, **changes: object
    ) -> StockAdjustmentApplicationSnapshot:
        """Собирает полный результат применения только по затронутым позициям."""
        return StockAdjustmentApplicationPolicy.build_snapshot(
            **(
                dict(
                    posting=self.posting.snapshot(),
                    execution=self.execution.adjustment_snapshot(),
                    positions_after=self.positions_after,
                    applied_at=self.f.f.time,
                )
                | changes
            )
        )

    def complete(self, **changes: object) -> InventoryCount:
        """Завершает корень по связанным историческим фактам без текущих складских снимков."""
        return self.count.complete_with_adjustment(
            **(
                dict(
                    result=self.result,
                    document=self.document.adjustment_completion_snapshot(),
                    execution=self.execution.adjustment_snapshot(),
                    posting=self.posting.snapshot(),
                    application=self.application,
                    expected_version=self.count.version,
                    updated_at=self.time,
                )
                | changes
            )
        )

    def restore(self, count: InventoryCount, **changes: object) -> InventoryCount:
        """Восстанавливает полный собственный состав без загрузки чужих агрегатов или результата."""
        values = {field.name: getattr(count, field.name) for field in fields(count)}
        values["identifier"] = values.pop("id")
        return InventoryCount.restore(**(values | changes))

    def zero_count(
        self, *, empty: bool = False, found_zero: bool = False
    ) -> tuple[InventoryCount, InventoryCountResultSnapshot]:
        """Регистрирует полностью совпавшие наблюдения либо явно пустой результат прежними фабриками."""
        f = self.f.f.f
        if empty:
            f.baseline = replace(f.baseline, positions=())
            f.sheets = ()
        else:
            f.sheets = (
                replace(
                    f.first,
                    lines=(
                        replace(
                            f.first.lines[0], counted_qty=f.first.lines[0].expected_qty
                        ),
                    ),
                ),
                f.second,
            )
            if found_zero:
                f.sheets = (*f.sheets, f.found(quantity="0"))
        self.f.f.refresh(**(dict(inventory_items=()) if empty else {}))
        return self.f.f.count, self.f.f.result

    def test_completion_keeps_only_compact_provenance_and_closes_root(self) -> None:
        """COUNTED → COMPLETED увеличивает версию, сохраняет ссылки и не меняет другие корни или исходный объект."""
        before = (
            self.count,
            self.document,
            self.execution,
            self.posting,
            self.application,
        )
        completed = self.complete()
        self.assertEqual(completed.status, InventoryCountStatus.COMPLETED)
        self.assertEqual(completed.version, self.count.version + 1)
        self.assertEqual(completed.baseline, self.count.baseline)
        self.assertEqual(completed.result, self.count.result)
        self.assertEqual(
            completed.completion,
            InventoryCountCompletionVO(
                self.time,
                self.document.id,
                self.document.version,
                self.execution.id,
                self.posting.id,
            ),
        )
        self.assertEqual(
            before,
            (self.count, self.document, self.execution, self.posting, self.application),
        )
        self.assertIsNone(self.count.completion)
        self.assertEqual(self.restore(completed), completed)

    def test_application_records_exact_ledger_results(self) -> None:
        """Снимок содержит все записи, реальные цели и одну следующую версию, включая FOUND v1."""
        by_position = {row.position.id: row for row in self.application.lines}
        self.assertEqual(
            {row.entry_id for row in self.application.lines},
            {entry.id for entry in self.posting.entries},
        )
        for line in self.execution.lines:
            position = by_position[line.route.position_id].position
            self.assertEqual(position.on_hand_qty, line.route.adjustment.target_qty)
            self.assertEqual(position.version, line.route.expected_position_version + 1)
        with self.assertRaises(FrozenInstanceError):
            self.application.posting_id = StockPostingIdVO(uuid4())

    def test_missing_application_or_planned_entry_cannot_close_count(self) -> None:
        """COMPLETED документа и существования Ledger недостаточно без полного результата применения."""
        entry = self.posting.adjustment_entries(self.execution.adjustment_snapshot())[0]
        for application in (None, entry, (entry,), self.positions_after):
            with (
                self.subTest(application=application),
                self.assertRaises(InventoryError),
            ):
                self.complete(application=application)
        with self.assertRaises(InventoryError):
            self.complete(posting=None)

    def test_initial_or_partial_position_results_are_rejected(self) -> None:
        """Исходные позиции до применения и изменение только части строк не доказывают полный переход."""
        before = tuple(
            position.counting_snapshot()
            for position in self.f.positions(self.execution)
            if position.id in {entry.position_id for entry in self.posting.entries}
        )
        for positions in (
            before,
            self.positions_after[:1],
            (),
            (*self.positions_after, self.positions_after[0]),
            list(self.positions_after),
        ):
            with self.subTest(positions=positions), self.assertRaises(InventoryError):
                self.build_application(positions_after=positions)

    def test_wrong_target_version_dimensions_or_unit_are_rejected(self) -> None:
        """Результат обязан точно совпадать с маршрутом, а не только иметь положительную версию."""
        original = self.positions_after[0]
        for position in (
            replace(original, on_hand_qty=QuantityVO(Decimal(1))),
            replace(original, version=original.version + 1),
            replace(
                original,
                dimensions=replace(
                    original.dimensions, stock_status=StockStatus.BLOCKED
                ),
            ),
            replace(original, base_uom=UomCodeVO("KG")),
        ):
            with self.subTest(position=position), self.assertRaises(InventoryError):
                self.build_application(
                    positions_after=(position, *self.positions_after[1:])
                )

    def test_application_header_and_entry_provenance_are_rechecked(self) -> None:
        """Сведения о применении нельзя перепривязать к иному Ledger, факту или ID записи."""
        for application in (
            replace(self.application, posting_id=StockPostingIdVO(uuid4())),
            replace(self.application, execution_id=StockExecutionIdVO(uuid4())),
            replace(
                self.application,
                lines=(
                    replace(
                        self.application.lines[0],
                        entry_id=StockLedgerEntryIdVO(uuid4()),
                    ),
                    *self.application.lines[1:],
                ),
            ),
            replace(self.application, lines=self.application.lines[:1]),
        ):
            with (
                self.subTest(application=application),
                self.assertRaises(InventoryError),
            ):
                self.complete(application=application)

    def test_result_must_be_exactly_registered_for_this_count(self) -> None:
        """Чужие ID, родитель, владелец, версия и основание результата не закрывают инвентаризацию."""
        variants = (
            replace(self.result, id=InventoryCountResultIdVO(uuid4())),
            replace(self.result, inventory_count_id=InventoryCountIdVO(uuid4())),
            replace(self.result, inventory_count_version=self.count.version),
            replace(
                self.result, prepared_at=self.result.prepared_at + timedelta(seconds=1)
            ),
        )
        for result in variants:
            with self.subTest(result=result), self.assertRaises(InventoryError):
                self.complete(result=result)

    def test_document_source_scope_version_and_full_execution_are_required(
        self,
    ) -> None:
        """Завершённый документ проверяется вместе с источником, областью и исторической версией факта."""
        document = self.document.adjustment_completion_snapshot()
        for value in (
            replace(document, source=replace(document.source, reference=str(uuid4()))),
            replace(document, version=document.version + 1),
            replace(document, status=StockDocumentStatus.CONFIRMED),
            replace(document, lines=document.lines[:1]),
            replace(
                document,
                lines=(
                    replace(document.lines[0], executed_qty=QuantityVO(Decimal(0))),
                    *document.lines[1:],
                ),
            ),
            replace(document, owner_id=document.owner_id.__class__(uuid4())),
        ):
            with self.subTest(document=value), self.assertRaises(InventoryError):
                self.complete(document=value)
        with self.assertRaises(InventoryError):
            self.f.document.adjustment_completion_snapshot()
        with self.assertRaises(InventoryError):
            self.document.adjustment_execution_snapshot()

    def test_completed_document_preserves_real_quantities_in_snapshot(self) -> None:
        """Снимок COMPLETED не подменяет состояние на CONFIRMED и сохраняет исторический SKU."""
        snapshot = self.document.adjustment_completion_snapshot()
        snapshot.ensure_valid()
        self.assertEqual(snapshot.status, StockDocumentStatus.COMPLETED)
        self.assertEqual(snapshot.version, self.document.version)
        for row in snapshot.lines:
            self.assertEqual(row.executed_qty, row.planned_qty)
            self.assertEqual(row.line.sku, self.document.get_line(row.line.id).sku)

    def test_tampered_sign_or_target_of_document_cannot_close_count(self) -> None:
        """Даже одинаковый модуль плана не позволяет заменить недостачу приходом."""
        document = self.document.adjustment_completion_snapshot()
        row = next(
            row
            for row in document.lines
            if row.line.adjustment.quantity_delta.value < 0
        )
        opposite = replace(
            row,
            line=replace(
                row.line,
                adjustment=replace(
                    row.line.adjustment, target_qty=QuantityVO(Decimal(123))
                ),
            ),
        )
        with self.assertRaises(InventoryError):
            self.complete(
                document=replace(
                    document,
                    lines=tuple(
                        opposite if value.line.id == row.line.id else value
                        for value in document.lines
                    ),
                )
            )

    def test_execution_and_posting_must_belong_to_completed_document(self) -> None:
        """Нельзя закрыть инвентаризацию по факту другой версии или с подменёнными знаками Ledger."""
        execution = self.execution.adjustment_snapshot()
        for value in (
            replace(execution, document_version=execution.document_version + 1),
            replace(execution, lines=execution.lines[:1]),
            replace(execution, warehouse_id=execution.warehouse_id.__class__(uuid4())),
        ):
            with self.subTest(execution=value), self.assertRaises(InventoryError):
                self.complete(execution=value)
        posting = self.posting.snapshot()
        entry = posting.entries[0]
        with self.assertRaises(InventoryError):
            self.complete(
                posting=replace(
                    posting,
                    entries=(
                        replace(
                            entry,
                            quantity_delta=StockDeltaVO(
                                entry.quantity_delta.value.copy_negate()
                            ),
                        ),
                        *posting.entries[1:],
                    ),
                )
            )

    def test_order_of_fact_and_application_rows_does_not_change_completion(
        self,
    ) -> None:
        """Проверка использует идентичность строк и записей, а не порядок коллекций."""
        document, execution = (
            self.document.adjustment_completion_snapshot(),
            self.execution.adjustment_snapshot(),
        )
        completed = self.complete(
            document=replace(document, lines=tuple(reversed(document.lines))),
            execution=replace(execution, lines=tuple(reversed(execution.lines))),
            application=replace(
                self.application, lines=tuple(reversed(self.application.lines))
            ),
        )
        self.assertEqual(completed.completion, self.complete().completion)
        self.assertEqual(
            self.build_application(
                positions_after=tuple(reversed(self.positions_after))
            ),
            self.application,
        )

    def test_late_completion_uses_recorded_application_not_live_stock(self) -> None:
        """Законный приход 10 после поправки 100→77 не мешает закрытию по сохранённому результату 77/v8."""
        changed = self.f.apply(self.posting, self.execution)
        position = next(
            position for position in changed if position.on_hand_qty.value == 77
        )
        later = position.apply_delta(
            StockDeltaVO(Decimal(10)), **self.f.position_context(position.dimensions)
        )
        self.assertEqual((later.on_hand_qty.value, later.version), (87, 9))
        self.assertEqual(
            self.complete(updated_at=self.time + timedelta(days=10)).status,
            InventoryCountStatus.COMPLETED,
        )
        with self.assertRaises(InventoryError):
            self.build_application(
                positions_after=tuple(
                    later.counting_snapshot() if row.id == later.id else row
                    for row in self.positions_after
                )
            )

    def test_zero_result_completes_without_documents_or_stock_changes(self) -> None:
        """Полное совпадение сохраняет только момент завершения, без фиктивных складских ссылок."""
        for empty, found_zero in ((False, False), (False, True), (True, False)):
            with self.subTest(empty=empty, found_zero=found_zero):
                self.f.setUp()
                count, result = self.zero_count(empty=empty, found_zero=found_zero)
                completed = count.complete_without_adjustment(
                    result=result, expected_version=count.version, updated_at=self.time
                )
                self.assertEqual(completed.status, InventoryCountStatus.COMPLETED)
                self.assertEqual(
                    completed.completion,
                    InventoryCountCompletionVO(self.time, None, None, None, None),
                )
                self.assertEqual(completed.version, count.version + 1)
                self.assertEqual(count.status, InventoryCountStatus.COUNTED)
                self.assertEqual(self.restore(completed), completed)

    def test_zero_result_can_close_after_subsequent_legal_movement(self) -> None:
        """Совпавшие исторические наблюдения не требуют замораживания склада до закрытия сессии."""
        count, result = self.zero_count()
        position = self.f.positions(self.execution)[0]
        later = position.apply_delta(
            StockDeltaVO(Decimal(10)), **self.f.position_context(position.dimensions)
        )
        self.assertEqual(later.version, position.version + 1)
        completed = count.complete_without_adjustment(
            result=result,
            expected_version=count.version,
            updated_at=self.time + timedelta(days=1),
        )
        self.assertEqual(completed.status, InventoryCountStatus.COMPLETED)

    def test_nonzero_result_requires_adjustment_path(self) -> None:
        """Ненулевые расхождения не закрываются веткой без корректировки."""
        with self.assertRaises(InventoryCountCompletionError):
            self.count.complete_without_adjustment(
                result=self.result,
                expected_version=self.count.version,
                updated_at=self.time,
            )

    def test_zero_result_cannot_close_with_unrelated_adjustment(self) -> None:
        """Нулевому зарегистрированному результату нельзя приписать сторонние документы и Ledger."""
        self.count, self.result = self.zero_count()
        with self.assertRaises(InventoryError):
            self.complete()

    def test_completion_version_and_status_are_strict(self) -> None:
        """Устаревшая/булева версия, иной статус и повторное завершение отклоняются до изменения корня."""
        for version in (True, -1, self.count.version - 1):
            with self.subTest(version=version), self.assertRaises(InventoryError):
                self.complete(expected_version=version)
        completed = self.complete()
        with self.assertRaises(InventoryError):
            completed.complete_with_adjustment(
                result=self.result,
                document=self.document.adjustment_completion_snapshot(),
                execution=self.execution.adjustment_snapshot(),
                posting=self.posting.snapshot(),
                application=self.application,
                expected_version=completed.version,
                updated_at=self.time,
            )
        with self.assertRaises(InventoryError):
            self.f.f.f.count.complete_without_adjustment(
                result=self.result,
                expected_version=self.f.f.f.count.version,
                updated_at=self.time,
            )

    def test_application_and_completion_time_must_follow_their_facts(self) -> None:
        """UTC-хронология проверяет проведение, применение, регистрацию документа и завершение сессии."""
        early = self.f.f.time - timedelta(seconds=1)
        with self.assertRaises(InventoryError):
            self.build_application(applied_at=early)
        with self.assertRaises(InventoryError):
            self.complete(updated_at=early)
        with self.assertRaises(InventoryError):
            self.complete(
                application=self.build_application(
                    applied_at=self.time + timedelta(seconds=1)
                )
            )
        with self.assertRaises(InventoryError):
            self.complete(
                document=replace(
                    self.document.adjustment_completion_snapshot(),
                    updated_at=self.time + timedelta(seconds=1),
                )
            )
        with self.assertRaises(InventoryError):
            self.complete(updated_at=self.time.replace(tzinfo=None))

    def test_completion_value_normalizes_time_and_enforces_reference_matrix(
        self,
    ) -> None:
        """VO проверяет собственные ссылки/версию и не пытается проверять существование чужих агрегатов."""
        valid = self.complete().completion
        shifted = valid.completed_at.astimezone(timezone(timedelta(hours=2)))
        self.assertEqual(replace(valid, completed_at=shifted), valid)
        for changes in (
            dict(document_version=True),
            dict(document_version=0),
            dict(document_version=-1),
            dict(execution_id=None),
            dict(posting_id=None),
            dict(document_id=None),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                replace(valid, **changes)

    def test_restore_requires_completion_only_in_completed_status(self) -> None:
        """Историческое восстановление проверяет собственные обязательные ссылки и момент, без свежего склада."""
        completed = self.complete()
        for changes in (
            dict(completion=None),
            dict(result=None),
            dict(baseline=None),
            dict(status=InventoryCountStatus.COUNTED),
            dict(
                completion=replace(
                    completed.completion, completed_at=self.time + timedelta(seconds=1)
                )
            ),
            dict(
                completion=replace(
                    completed.completion,
                    completed_at=self.f.f.time - timedelta(seconds=1),
                )
            ),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.restore(completed, **changes)
        with self.assertRaises(InventoryError):
            self.restore(self.count, completion=completed.completion)

    def test_closed_count_snapshots_represent_history_without_reopening_operations(
        self,
    ) -> None:
        """COMPLETED представим снимками, но не разрешает новые ведомости, корректировки, факты или изменения."""
        completed = self.complete()
        source = completed.adjustment_source_snapshot()
        source.ensure_valid()
        completed.sheet_source_snapshot().ensure_valid()
        completed.start_plan_snapshot().ensure_valid()
        self.assertEqual(source.result, completed.result)
        with self.assertRaises(InventoryError):
            CountSheetSourcePolicy.ensure_compatible(
                inventory_count=completed.sheet_source_snapshot(),
                baseline=self.f.context["baseline"],
            )
        with self.assertRaises(InventoryError):
            self.f.f.build(inventory_count=source)
        with self.assertRaises(InventoryError):
            self.f.execute(inventory_count=source)
        with self.assertRaises(InventoryError):
            self.f.post(self.execution, inventory_count=source)
        for operation in (
            lambda: completed.change_scope(
                completed.scope,
                expected_version=completed.version,
                updated_at=self.time,
            ),
            lambda: completed.cancel(
                expected_version=completed.version, updated_at=self.time
            ),
            lambda: completed.confirm(
                expected_version=completed.version,
                warehouse=self.f.f.warehouse,
                updated_at=self.time,
            ),
            lambda: completed.start(
                self.f.context["baseline"],
                expected_version=completed.version,
                warehouse=self.f.f.warehouse,
                locations=self.f.context["locations"],
                updated_at=self.time,
            ),
        ):
            with self.assertRaises(InventoryError):
                operation()

    def test_serial_relocation_closes_with_two_application_rows(self) -> None:
        """Исторические результаты −1/+1 одного SERIAL закрываются без повторного запроса его присутствия."""
        self.f.serial_relocation()
        self.prepare_evidence()
        self.assertEqual(len(self.application.lines), 2)
        self.assertEqual(self.complete().status, InventoryCountStatus.COMPLETED)

    def test_found_only_result_closes_with_new_position_version_one(self) -> None:
        """Пустое основание с найденными 5 завершается по реально подготовленной новой позиции, сохраняя None в источнике."""
        f = self.f.f.f
        dimensions = replace(
            f.baseline.positions[0].dimensions, stock_status=StockStatus.DAMAGED
        )
        f.baseline = replace(f.baseline, positions=())
        f.sheets = (f.found(dimensions=dimensions),)
        self.f.f.refresh()
        self.f.prepare()
        self.prepare_evidence()
        self.assertEqual(len(self.application.lines), 1)
        self.assertEqual(self.application.lines[0].position.version, 1)
        self.assertIsNone(self.execution.lines[0].route.adjustment.position_id)
        self.assertEqual(self.complete().status, InventoryCountStatus.COMPLETED)

    def test_composite_sheet_line_sources_remain_distinct_at_completion(self) -> None:
        """Локально одинаковый ID наблюдения двух ведомостей не объединяется в итоговой цепочке."""
        f = self.f.f.f
        first, zero, found = f.sheets
        f.sheets = (
            first,
            zero,
            replace(found, lines=(replace(found.lines[0], id=first.lines[0].id),)),
        )
        self.f.f.refresh()
        self.f.prepare()
        self.prepare_evidence()
        self.assertEqual(len(self.application.lines), 2)
        self.assertEqual(self.complete().status, InventoryCountStatus.COMPLETED)

    def test_application_snapshot_rejects_raw_duplicate_or_naive_values(self) -> None:
        """Публичная граница проверяет номинальные снимки, tuple, UTC и уникальные записи."""
        for changes in (
            dict(lines=list(self.application.lines)),
            dict(lines=(None,)),
            dict(lines=(*self.application.lines, self.application.lines[0])),
            dict(applied_at=self.application.applied_at.replace(tzinfo=None)),
            dict(
                lines=(
                    replace(
                        self.application.lines[0],
                        position=replace(
                            self.application.lines[0].position, version=True
                        ),
                    ),
                    *self.application.lines[1:],
                )
            ),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.complete(application=replace(self.application, **changes))
        for value in (None, True, -1):
            with (
                self.subTest(document_version=value),
                self.assertRaises(InventoryError),
            ):
                self.complete(
                    document=replace(
                        self.document.adjustment_completion_snapshot(), version=value
                    )
                )


if __name__ == "__main__":
    unittest.main()
