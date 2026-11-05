"""Полная корректировка: факт, Ledger, переход физических позиций и завершение документа."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_count_adjustment_document_domain as document_fixture
from src.modules.inventory.domain.error import (
    InventoryError,
    StockAdjustmentError,
    QuantityStepError,
)
from src.modules.inventory.domain.availability_pool.aggregate import AvailabilityPool
from src.modules.inventory.domain.availability_pool.value_object.identifier import (
    AvailabilityPoolIdVO,
)
from src.modules.inventory.domain.availability_pool.value_object.key import (
    AvailabilityPoolKeyVO,
)
from src.modules.inventory.domain.inventory_item.availability_snapshot import (
    InventoryItemAvailabilitySnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.domain.inventory_count.error import (
    InventoryCountBaselineChangedError,
)
from src.modules.inventory.domain.inventory_count.value_object.status import (
    InventoryCountStatus,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.policy.stock_serial_presence import (
    StockSerialPresencePolicy,
)
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.value_object.adjustment_line_binding import (
    StockAdjustmentExecutionLineBindingVO,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_position.aggregate import StockPosition
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
from src.modules.inventory.domain.stock_posting.value_object.posting_source import (
    PostingSourceVO,
)
from src.modules.inventory.domain.stock_serial.presence_snapshot import (
    StockSerialPresenceSnapshot,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class AdjustmentApplicationDomainTests(unittest.TestCase):
    """Проверяет всю цепочку на самостоятельных immutable агрегатах без Application и SQL."""

    def setUp(self) -> None:
        """Готовит подтверждённую поправку 100→77, FOUND 0→5 и неизменяемую нулевую позицию."""
        self.f = document_fixture.InventoryCountAdjustmentDocumentDomainTests()
        self.f.setUp()
        self.prepare()

    def prepare(self) -> None:
        """Строит документ по текущему зарегистрированному результату тестового контекста."""
        self.document = self.f.confirm(self.f.build())
        self.context = self.f.context()
        self.bindings = tuple(
            StockAdjustmentExecutionLineBindingVO(
                line.id,
                StockExecutionLineIdVO(uuid4()),
                line.adjustment.position_id or StockPositionIdVO(uuid4()),
            )
            for line in self.document.lines
        )
        self.presence = tuple(
            StockSerialPresenceSnapshot(
                serial_id,
                tuple(
                    position
                    for position in self.context["positions"]
                    if position.dimensions.serial_id == serial_id
                    and position.on_hand_qty.value == 1
                ),
            )
            for serial_id in {
                line.adjustment.dimensions.serial_id
                for line in self.document.lines
                if line.adjustment.dimensions.serial_id is not None
            }
        )

    def execute(self, **changes: object) -> StockExecution:
        """Фиксирует полный факт, каждый раз передавая всё текущее исходное основание."""
        return StockExecution.create_from_inventory_count_adjustment(
            **(
                self.context
                | dict(
                    identifier=StockExecutionIdVO(uuid4()),
                    document=self.document.adjustment_execution_snapshot(),
                    bindings=self.bindings,
                    executed_at=self.f.time,
                    presence=self.presence,
                )
                | changes
            )
        )

    def stock_item(self) -> InventoryItemStockSnapshot:
        """Передаёт текущие физические правила без SKU и коллекций карточки."""
        item = self.f.item
        return InventoryItemStockSnapshot(
            item.inventory_item_id,
            item.base_uom,
            item.quantity_rules,
            item.tracking_mode,
        )

    def position_context(self, dimensions: StockDimensionsVO) -> dict[str, object]:
        """Находит текущие снимки справочников для одной позиции."""
        return dict(
            inventory_item=self.stock_item(),
            warehouse=self.f.warehouse,
            location=next(
                location
                for location in self.context["locations"]
                if location.id == dimensions.location_id
            ),
            lot=next(
                (
                    lot
                    for lot in self.context.get("lots", ())
                    if lot.id == dimensions.lot_id
                ),
                None,
            ),
            serial=next(
                (
                    serial
                    for serial in self.context.get("serials", ())
                    if serial.id == dimensions.serial_id
                ),
                None,
            ),
        )

    def found(self, execution: StockExecution) -> tuple[StockPosition, ...]:
        """Создаёт новые нулевые позиции явной фабрикой после проверки исходного основания."""
        return tuple(
            StockPosition.create(
                identifier=line.route.position_id,
                dimensions=line.route.adjustment.dimensions,
                **self.position_context(line.route.adjustment.dimensions),
            )
            for line in execution.lines
            if line.route.adjustment.position_id is None
        )

    def post(self, reference: StockExecution, **changes: object) -> StockPosting:
        """Заново проверяет полный исходный запас и передаёт FOUND отдельно от исторического основания."""
        return StockPosting.create_from_adjustment_execution(
            **(
                self.context
                | dict(
                    identifier=StockPostingIdVO(uuid4()),
                    execution=reference.adjustment_snapshot(),
                    document=self.document.adjustment_execution_snapshot(),
                    posted_at=self.f.time,
                    found_positions=tuple(
                        position.counting_snapshot()
                        for position in self.found(reference)
                    ),
                    entry_bindings=tuple(
                        StockPostingEntryBindingVO(
                            line.route.position_id, StockLedgerEntryIdVO(uuid4())
                        )
                        for line in reference.lines
                    ),
                    presence=self.presence,
                )
                | changes
            )
        )

    def positions(self, execution: StockExecution) -> tuple[StockPosition, ...]:
        """Восстанавливает исходные реальные позиции и добавляет отдельно новые нулевые кандидаты."""
        return tuple(
            StockPosition.restore(
                identifier=position.id,
                dimensions=position.dimensions,
                base_uom=position.base_uom,
                on_hand_qty=position.on_hand_qty,
                version=position.version,
            )
            for position in self.context["positions"]
        ) + self.found(execution)

    def apply(
        self, posting: StockPosting, execution: StockExecution
    ) -> tuple[StockPosition, ...]:
        """Вызывает собственный метод каждого корня, сохраняя исходные объекты неизменными."""
        entries = {
            snapshot.entry.position_id: snapshot
            for snapshot in posting.adjustment_entries(execution.adjustment_snapshot())
        }
        return tuple(
            (
                position
                if position.id not in entries
                else position.apply_adjustment_entry(
                    entries[position.id],
                    expected_version=position.version,
                    **self.position_context(position.dimensions),
                )
            )
            for position in self.positions(execution)
        )

    def restore_execution(
        self, execution: StockExecution, **changes: object
    ) -> StockExecution:
        """Восстанавливает полный исторический факт без текущих источников."""
        values = {
            field.name: getattr(execution, field.name) for field in fields(execution)
        }
        values["identifier"] = values.pop("id")
        return StockExecution.restore(**(values | changes))

    def test_full_chain_preserves_history_and_completes_document(self) -> None:
        """Факт и Ledger не меняют запас; применение даёт 77/v8 и FOUND 5/v1, документ COMPLETED."""
        before = (
            self.document,
            self.f.count,
            self.context["baseline"],
            self.context["positions"],
        )
        execution = self.execute()
        posting = self.post(execution)
        self.assertEqual(
            {entry.quantity_delta.value for entry in posting.entries},
            {Decimal(-23), Decimal(5)},
        )
        self.assertEqual(posting.source.execution_id, execution.id)
        self.assertEqual(
            before,
            (
                self.document,
                self.f.count,
                self.context["baseline"],
                self.context["positions"],
            ),
        )
        changed = self.apply(posting, execution)
        by_id = {position.id: position for position in changed}
        for line in execution.lines:
            position = by_id[line.route.position_id]
            self.assertEqual(position.on_hand_qty, line.route.adjustment.target_qty)
            self.assertEqual(position.version, line.route.expected_position_version + 1)
            if line.route.adjustment.position_id is None:
                self.assertIsNone(line.route.adjustment.position_version)
        completed = self.document.register_adjustment_execution(
            execution.adjustment_snapshot(), updated_at=self.f.time
        )
        self.assertEqual(completed.status, StockDocumentStatus.COMPLETED)
        self.assertEqual(completed.version, self.document.version + 1)
        self.assertTrue(
            all(line.executed_qty == line.planned_qty for line in completed.lines)
        )
        self.assertEqual(self.f.count.status, InventoryCountStatus.COUNTED)
        self.assertEqual(self.document.status, StockDocumentStatus.CONFIRMED)
        self.assertEqual(self.f.restore(completed), completed)

    def test_each_document_line_executes_once_in_full(self) -> None:
        """Пропуски, повторные ID фактов, повтор позиции и сырые назначения запрещены."""
        for bindings in (
            (),
            self.bindings[:1],
            (*self.bindings, self.bindings[0]),
            list(self.bindings),
            (None,),
            (
                self.bindings[0],
                replace(
                    self.bindings[1],
                    execution_line_id=self.bindings[0].execution_line_id,
                ),
            ),
            (
                self.bindings[0],
                replace(self.bindings[1], position_id=self.bindings[0].position_id),
            ),
        ):
            with self.subTest(bindings=bindings), self.assertRaises(InventoryError):
                self.execute(bindings=bindings)

    def test_only_confirmed_plan_can_execute(self) -> None:
        """Черновик, отменённый и уже завершённый документ не выдают исполняемый план."""
        for document in (self.f.build(), self.document.cancel(updated_at=self.f.time)):
            with (
                self.subTest(status=document.status),
                self.assertRaises(StockAdjustmentError),
            ):
                document.adjustment_execution_snapshot()
        execution = self.execute()
        completed = self.document.register_adjustment_execution(
            execution.adjustment_snapshot(), updated_at=self.f.time
        )
        with self.assertRaises(InventoryError):
            completed.register_adjustment_execution(
                execution.adjustment_snapshot(), updated_at=self.f.time
            )

    def test_full_baseline_is_checked_again_before_execution_and_posting(self) -> None:
        """Изменение даже неизменяемой нулевой позиции блокирует факт и проведение."""
        execution = self.execute()
        original = self.context["positions"]
        changes = (
            original[:1],
            (original[0], replace(original[1], version=1)),
            (replace(original[0], on_hand_qty=QuantityVO(Decimal(99))), original[1]),
        )
        for positions in changes:
            with self.subTest(positions=positions):
                with self.assertRaises(InventoryCountBaselineChangedError):
                    self.execute(positions=positions)
                with self.assertRaises(InventoryCountBaselineChangedError):
                    self.post(execution, positions=positions)

    def test_new_positions_or_locations_in_original_scope_make_baseline_stale(
        self,
    ) -> None:
        """Конкурентный приход FOUND и новый адрес полной области не обходят проверку старых ID."""
        execution = self.execute()
        new = self.found(execution)[0].counting_snapshot()
        with self.assertRaises(InventoryCountBaselineChangedError):
            self.post(execution, positions=(*self.context["positions"], new))
        location = replace(self.context["locations"][0], id=StockLocationIdVO(uuid4()))
        with self.assertRaises(InventoryCountBaselineChangedError):
            self.execute(locations=(*self.context["locations"], location))

    def test_registered_result_and_parent_are_rechecked(self) -> None:
        """COUNTED и точный зарегистрированный результат остаются обязательны на обоих этапах."""
        execution = self.execute()
        parent = self.context["inventory_count"]
        for changes in (
            dict(
                inventory_count=replace(
                    parent, status=InventoryCountStatus.IN_PROGRESS, result=None
                )
            ),
            dict(
                result=replace(
                    self.context["result"], inventory_count_version=parent.version
                )
            ),
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(InventoryError):
                    self.execute(**changes)
                with self.assertRaises(InventoryError):
                    self.post(execution, **changes)

    def test_found_is_a_new_position_without_rewriting_source(self) -> None:
        """Новый ноль версии 0 отделён от None в историческом источнике, переиспользование старого ID запрещено."""
        found = next(
            binding
            for binding in self.bindings
            if self.document.get_line(binding.document_line_id).adjustment.position_id
            is None
        )
        old_id = self.context["positions"][1].id
        with self.assertRaises(StockAdjustmentError):
            self.execute(
                bindings=tuple(
                    (
                        replace(binding, position_id=old_id)
                        if binding == found
                        else binding
                    )
                    for binding in self.bindings
                )
            )
        execution = self.execute()
        position = self.found(execution)[0]
        self.assertEqual((position.on_hand_qty.value, position.version), (0, 0))
        self.assertIsNone(
            next(
                line.route
                for line in execution.lines
                if line.route.position_id == position.id
            ).adjustment.position_id
        )

    def test_posting_requires_exactly_new_zero_found_positions(self) -> None:
        """Нельзя пропустить FOUND, передать иной ID/версию/количество или лишнюю позицию."""
        execution = self.execute()
        position = self.found(execution)[0].counting_snapshot()
        for found in (
            (),
            (replace(position, version=1),),
            (replace(position, on_hand_qty=QuantityVO(Decimal(1))),),
            (replace(position, id=StockPositionIdVO(uuid4())),),
            (position, position),
            list((position,)),
        ):
            with self.subTest(found=found), self.assertRaises(InventoryError):
                self.post(execution, found_positions=found)

    def test_execution_keeps_sign_target_and_document_version(self) -> None:
        """Факт с другой версией, целью или знаком нельзя провести или зарегистрировать."""
        execution = self.execute()
        snapshot = execution.adjustment_snapshot()
        row = next(
            line
            for line in snapshot.lines
            if line.route.adjustment.quantity_delta.value < 0
        )
        opposite = replace(
            row,
            route=replace(
                row.route,
                adjustment=replace(
                    row.route.adjustment, target_qty=QuantityVO(Decimal(123))
                ),
            ),
        )
        for changed in (
            replace(snapshot, document_version=snapshot.document_version + 1),
            replace(snapshot, lines=snapshot.lines[:1]),
            replace(
                snapshot,
                lines=tuple(
                    opposite if line.id == row.id else line for line in snapshot.lines
                ),
            ),
        ):
            with self.subTest(fact=changed):
                with self.assertRaises(InventoryError):
                    self.post(execution, execution=changed)
                with self.assertRaises(InventoryError):
                    self.document.register_adjustment_execution(
                        changed, updated_at=self.f.time
                    )

    def test_ledger_bindings_are_complete_unique_and_not_netted(self) -> None:
        """У каждой позиции своя запись, без пропусков, повторов или нулевого общего итога."""
        execution = self.execute()
        bindings = tuple(
            StockPostingEntryBindingVO(
                line.route.position_id, StockLedgerEntryIdVO(uuid4())
            )
            for line in execution.lines
        )
        for values in (
            (),
            bindings[:1],
            (*bindings, bindings[0]),
            (bindings[0], replace(bindings[1], entry_id=bindings[0].entry_id)),
        ):
            with self.subTest(bindings=values), self.assertRaises(InventoryError):
                self.post(execution, entry_bindings=values)

    def test_application_matches_full_ledger_to_execution(self) -> None:
        """Подмена знака/единицы/основания либо неполный Ledger не выдаёт снимки для применения."""
        execution = self.execute()
        posting = self.post(execution)
        entry = posting.entries[0]
        variants = (
            replace(posting, source=PostingSourceVO(StockExecutionIdVO(uuid4()))),
            replace(posting, entries=posting.entries[:1]),
            replace(
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
            ),
        )
        for value in variants:
            with self.subTest(posting=value), self.assertRaises(InventoryError):
                value.adjustment_entries(execution.adjustment_snapshot())

    def test_position_rechecks_version_quantity_dimensions_and_current_step(
        self,
    ) -> None:
        """Проверка перед применением сохраняет защиту от изменений после подготовки Ledger."""
        execution = self.execute()
        posting = self.post(execution)
        snapshot = next(
            value
            for value in posting.adjustment_entries(execution.adjustment_snapshot())
            if value.route.adjustment.position_id is not None
        )
        position = next(
            value
            for value in self.positions(execution)
            if value.id == snapshot.entry.position_id
        )
        for changed in (
            replace(position, version=position.version + 1),
            replace(position, on_hand_qty=QuantityVO(Decimal(99))),
            replace(
                position,
                dimensions=replace(
                    position.dimensions, stock_status=StockStatus.BLOCKED
                ),
            ),
        ):
            with self.subTest(position=changed), self.assertRaises(InventoryError):
                changed.apply_adjustment_entry(
                    snapshot,
                    expected_version=changed.version,
                    **self.position_context(changed.dimensions),
                )
        with self.assertRaises(QuantityStepError):
            position.apply_adjustment_entry(
                snapshot,
                expected_version=position.version,
                **(
                    self.position_context(position.dimensions)
                    | dict(
                        inventory_item=replace(
                            self.stock_item(),
                            quantity_rules=QuantityRulesVO(Decimal(2)),
                        )
                    )
                ),
            )
        with self.assertRaises(InventoryError):
            position.apply_adjustment_entry(
                snapshot,
                expected_version=True,
                **self.position_context(position.dimensions),
            )

    def test_reapplying_entry_is_rejected_by_original_position_version(self) -> None:
        """Одна запись не меняет одну физическую позицию дважды даже при новой expected_version от вызывающего кода."""
        execution = self.execute()
        posting = self.post(execution)
        snapshots = {
            value.entry.position_id: value
            for value in posting.adjustment_entries(execution.adjustment_snapshot())
        }
        for position in self.apply(posting, execution):
            if position.id in snapshots:
                with self.assertRaises(InventoryError):
                    position.apply_adjustment_entry(
                        snapshots[position.id],
                        expected_version=position.version,
                        **self.position_context(position.dimensions),
                    )

    def test_ordinary_projections_and_raw_posting_remain_closed(self) -> None:
        """Корректировка не маскируется под расход, погашение резервов или упрощённый положительный итог."""
        execution = self.execute()
        for getter in (
            execution.snapshot_for_document,
            execution.posting_snapshot,
            execution.shipment_snapshot,
            execution.reservation_snapshot,
        ):
            with self.subTest(getter=getter), self.assertRaises(StockAdjustmentError):
                getter()
        posting = self.post(execution)
        with self.assertRaises(StockAdjustmentError):
            StockPosting.create(
                identifier=StockPostingIdVO(uuid4()),
                source=posting.source,
                operation_type=StockOperationType.ADJUSTMENT,
                posted_at=self.f.time,
                entries=posting.entries,
                positions=(),
            )
        with self.assertRaises(StockAdjustmentError):
            StockPosting.create_reversal(
                identifier=StockPostingIdVO(uuid4()),
                source=PostingSourceVO(StockExecutionIdVO(uuid4())),
                posted_at=self.f.time,
                original=posting.snapshot(),
                entry_ids=tuple(StockLedgerEntryIdVO(uuid4()) for _ in posting.entries),
                positions=(),
            )

    def test_restore_preserves_completed_history_without_live_context(self) -> None:
        """Сохранённые факты и Ledger восстанавливаются полностью без проверки новых правил товара."""
        execution = self.execute()
        posting = self.post(execution)
        self.assertEqual(self.restore_execution(execution), execution)
        values = {field.name: getattr(posting, field.name) for field in fields(posting)}
        values["identifier"] = values.pop("id")
        self.assertEqual(StockPosting.restore(**values), posting)
        with self.assertRaises(InventoryError):
            StockPosting.restore(
                **(values | dict(reversal_of_id=StockPostingIdVO(uuid4())))
            )
        with self.assertRaises(FrozenInstanceError):
            execution.document_version = 7

    def test_time_order_is_explicit_and_monotone(self) -> None:
        """Исполнение, проведение и регистрация не могут предшествовать своим основаниям."""
        early = self.f.time - timedelta(seconds=1)
        with self.assertRaises(InventoryError):
            self.execute(executed_at=early)
        execution = self.execute()
        with self.assertRaises(InventoryError):
            self.post(execution, posted_at=early)
        with self.assertRaises(InventoryError):
            self.document.register_adjustment_execution(
                execution.adjustment_snapshot(), updated_at=early
            )

    def test_legacy_step_positive_and_negative_deltas_are_exact(self) -> None:
        """Исторические 100.1 KG корректируются до 100.2/+0.1 или 100.0/−0.1 при шаге 0.2."""
        for target in ("100.2", "100.0"):
            with self.subTest(target=target):
                f = self.f.f
                f.item = replace(
                    f.item,
                    base_uom=UomCodeVO("KG"),
                    quantity_rules=QuantityRulesVO(Decimal("0.2")),
                )
                positions = tuple(
                    replace(
                        position,
                        base_uom=UomCodeVO("KG"),
                        on_hand_qty=QuantityVO(
                            Decimal("100.1") if index == 0 else Decimal(0)
                        ),
                    )
                    for index, position in enumerate(f.baseline.positions)
                )
                f.baseline = replace(f.baseline, positions=positions)
                f.sheets = tuple(
                    replace(
                        sheet,
                        lines=(
                            replace(
                                sheet.lines[0],
                                base_uom=UomCodeVO("KG"),
                                expected_qty=positions[index].on_hand_qty,
                                counted_qty=QuantityVO(
                                    Decimal(target) if index == 0 else Decimal(0)
                                ),
                            ),
                        ),
                    )
                    for index, sheet in enumerate((f.first, f.second))
                )
                self.f.refresh()
                self.prepare()
                with localcontext() as context:
                    context.prec = 1
                    context.traps[Inexact] = context.traps[Rounded] = True
                    execution = self.execute()
                    posting = self.post(execution)
                    changed = next(
                        position
                        for position in self.apply(posting, execution)
                        if position.id == positions[0].id
                    )
                    self.assertEqual(changed.on_hand_qty.value, Decimal(target))
                    self.assertEqual(changed.version, 8)
                    self.assertEqual(
                        posting.entries[0].quantity_delta.value.copy_abs(),
                        Decimal("0.1"),
                    )

    def serial_relocation(self) -> None:
        """Готовит SERIAL 1→0 в A и FOUND 0→1 в B."""
        f = self.f.f
        serial = f.serial_sources("0")
        f.sheets = (*f.sheets, f.found(quantity="1", serial=serial))
        self.f.refresh(serials=(serial,))
        self.prepare()

    def test_serial_relocation_keeps_minus_and_plus_and_one_final_presence(
        self,
    ) -> None:
        """Один экземпляр проходит двумя направлениями без сальдирования и дублирования конечного запаса."""
        self.serial_relocation()
        execution = self.execute()
        posting = self.post(execution)
        self.assertEqual(
            {entry.quantity_delta.value for entry in posting.entries},
            {Decimal(-1), Decimal(1)},
        )
        changed = self.apply(posting, execution)
        self.assertEqual(sum(position.on_hand_qty.value for position in changed), 1)
        self.document.register_adjustment_execution(
            execution.adjustment_snapshot(), updated_at=self.f.time
        )
        routes = tuple(line.route for line in reversed(execution.lines))
        StockSerialPresencePolicy.ensure_compatible(
            routes=routes, presence=self.presence
        )

    def test_serial_missing_stale_or_wrong_presence_blocks_execution(self) -> None:
        """Явное отсутствие не заменяет текущую единицу SERIAL, а её версия должна быть свежей."""
        self.serial_relocation()
        current = self.presence[0]
        for presence in (
            (),
            (replace(current, positions=()),),
            (current, current),
            (replace(current, positions=(replace(current.positions[0], version=99),)),),
        ):
            with (
                self.subTest(presence=presence),
                self.assertRaises(StockAdjustmentError),
            ):
                self.execute(presence=presence)

    def test_serial_found_cannot_duplicate_presence_outside_count_scope(self) -> None:
        """FOUND SERIAL не создаётся при положительном остатке вне пересчитанной области или у другого владельца."""
        self.serial_relocation()
        f = self.f.f
        f.baseline = replace(f.baseline, positions=())
        f.sheets = (f.sheets[1],)
        serial = self.context["serials"][0]
        self.f.refresh(serials=(serial,))
        self.prepare()
        external = replace(
            self.found(self.execute())[0].counting_snapshot(),
            id=StockPositionIdVO(uuid4()),
            dimensions=replace(
                self.document.lines[0].adjustment.dimensions,
                location_id=StockLocationIdVO(uuid4()),
            ),
            on_hand_qty=QuantityVO(Decimal(1)),
            version=3,
        )
        with self.assertRaises(StockAdjustmentError):
            self.execute(
                presence=(StockSerialPresenceSnapshot(serial.id, (external,)),)
            )

    def test_serial_presence_is_rechecked_before_posting(self) -> None:
        """Изменившееся после факта присутствие блокирует подготовку Ledger."""
        self.serial_relocation()
        execution = self.execute()
        changed = replace(self.presence[0], positions=())
        with self.assertRaises(StockAdjustmentError):
            self.post(execution, presence=(changed,))

    def test_inactive_physical_addresses_are_counted_without_sale_filters(self) -> None:
        """Корректировка физического учёта сохраняет адрес даже после выключения активности."""
        self.context["locations"] = tuple(
            replace(location, is_active=False) for location in self.context["locations"]
        )
        execution = self.execute()
        self.apply(self.post(execution), execution)
        with self.assertRaises(InventoryError):
            self.execute(warehouse=replace(self.f.warehouse, is_active=False))

    def test_lots_keep_separate_ledger_and_recheck_current_identity(self) -> None:
        """Равные противоположные поправки разных партий не сальдируются и не меняют принадлежность товара."""
        f = self.f.f
        f.item = replace(f.item, tracking_mode=TrackingMode.LOT)
        lots = tuple(
            StockLotSnapshot(
                StockLotIdVO(uuid4()),
                f.item.inventory_item_id,
                StockDatesVO(expires_on=self.f.time.date() - timedelta(days=1)),
            )
            for _ in range(2)
        )
        positions = tuple(
            replace(
                position, dimensions=replace(position.dimensions, lot_id=lots[index].id)
            )
            for index, position in enumerate(f.baseline.positions)
        )
        f.baseline = replace(f.baseline, positions=positions)
        f.sheets = tuple(
            replace(
                sheet,
                lines=(
                    replace(
                        sheet.lines[0],
                        dimensions=positions[index].dimensions,
                        counted_qty=QuantityVO(
                            Decimal(77) if index == 0 else Decimal(23)
                        ),
                    ),
                ),
            )
            for index, sheet in enumerate((f.first, f.second))
        )
        self.f.refresh()
        self.f.extra = dict(lots=lots)
        self.prepare()
        execution = self.execute()
        posting = self.post(execution)
        self.assertEqual(
            {entry.quantity_delta.value for entry in posting.entries},
            {Decimal(-23), Decimal(23)},
        )
        self.assertEqual(len(posting.entries), 2)
        changed = self.apply(posting, execution)
        self.assertEqual(
            {position.dimensions.lot_id for position in changed},
            {lot.id for lot in lots},
        )
        wrong = replace(
            lots[0], inventory_item_id=lots[0].inventory_item_id.__class__(uuid4())
        )
        with self.assertRaises(InventoryError):
            self.post(execution, lots=(wrong, lots[1]))

    def test_lot_and_serial_relocation_preserves_joint_identity(self) -> None:
        """Совместный LOT_AND_SERIAL переносит экземпляр двумя строками в той же партии."""
        f = self.f.f
        serial = f.serial_sources("0")
        f.sheets = (*f.sheets, f.found(quantity="1", serial=serial))
        lot = StockLotSnapshot(
            StockLotIdVO(uuid4()), f.item.inventory_item_id, StockDatesVO()
        )
        serial = replace(serial, lot_id=lot.id)
        f.item = replace(f.item, tracking_mode=TrackingMode.LOT_AND_SERIAL)
        position = replace(
            f.baseline.positions[0],
            dimensions=replace(f.baseline.positions[0].dimensions, lot_id=lot.id),
        )
        f.baseline = replace(f.baseline, positions=(position,))
        f.sheets = tuple(
            replace(
                sheet,
                lines=(
                    replace(
                        sheet.lines[0],
                        dimensions=replace(sheet.lines[0].dimensions, lot_id=lot.id),
                    ),
                ),
            )
            for sheet in f.sheets
        )
        self.f.refresh(lots=(lot,), serials=(serial,))
        self.prepare()
        execution = self.execute()
        self.apply(self.post(execution), execution)
        self.assertEqual(len(execution.lines), 2)
        self.assertEqual(execution.lines[0].route.adjustment.dimensions.lot_id, lot.id)
        with self.assertRaises(InventoryError):
            self.post(
                execution, serials=(replace(serial, lot_id=StockLotIdVO(uuid4())),)
            )

    def test_deficit_refresh_preserves_existing_reservations(self) -> None:
        """Недостача уменьшает пригодность до 77, сохраняя резерв 90 и показывая дефицит 13."""
        item = self.f.item
        key = AvailabilityPoolKeyVO(
            item.inventory_item_id, self.document.warehouse_id, self.document.owner_id
        )
        pool = AvailabilityPool.restore(
            identifier=AvailabilityPoolIdVO(uuid4()),
            key=key,
            base_uom=item.base_uom,
            eligible_qty=QuantityVO(Decimal(100)),
            reserved_qty=QuantityVO(Decimal(90)),
            assessed_on=self.f.time.date(),
            version=3,
        )
        execution = self.execute()
        changed = self.apply(self.post(execution), execution)
        refreshed = pool.refresh_eligible_quantity(
            expected_version=pool.version,
            inventory_item=InventoryItemAvailabilitySnapshot(
                item.inventory_item_id,
                item.base_uom,
                item.quantity_rules,
                item.tracking_mode,
                ExpirationMode.NONE,
            ),
            warehouse=self.f.warehouse,
            as_of=self.f.time.date(),
            positions=tuple(position.availability_snapshot() for position in changed),
            locations=self.context["locations"],
        )
        self.assertEqual(refreshed.reserved_qty.value, 90)
        self.assertEqual(refreshed.available_qty.value, 0)
        self.assertEqual(refreshed.deficit_qty.value, 13)
        self.assertEqual(pool.eligible_qty.value, 100)

    def test_fact_restore_rejects_partial_quantity_and_duplicate_document_line(
        self,
    ) -> None:
        """Даже историческое восстановление проверяет точный модуль поправки и единственную строку на источник."""
        execution = self.execute()
        original = execution.lines[0]
        partial = replace(
            original,
            quantity=QuantityVO(Decimal(1)),
            conversion=QuantityConversionSnapshotVO(
                QuantityVO(Decimal(1)), original.base_uom, Decimal(1)
            ),
        )
        for lines in (
            (partial, *execution.lines[1:]),
            (original, replace(original, id=StockExecutionLineIdVO(uuid4()))),
        ):
            with self.subTest(lines=lines), self.assertRaises(InventoryError):
                self.restore_execution(execution, lines=lines)

    def test_partial_document_progress_is_not_a_valid_adjustment_state(self) -> None:
        """COMPLETED требует полного факта каждой строки, а PARTIALLY_EXECUTED недопустим."""
        line = self.document.lines[0]
        for status in (
            StockDocumentStatus.COMPLETED,
            StockDocumentStatus.PARTIALLY_EXECUTED,
        ):
            with self.subTest(status=status), self.assertRaises(InventoryError):
                self.f.restore(
                    self.document,
                    status=status,
                    lines=(
                        replace(line, executed_qty=line.planned_qty),
                        *self.document.lines[1:],
                    ),
                )


if __name__ == "__main__":
    unittest.main()
