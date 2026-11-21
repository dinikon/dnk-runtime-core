"""Производный ADJUSTMENT: точные цели, полное основание и подтверждение без физического исполнения."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta
from decimal import Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from test import test_inventory_count_result_domain as result_fixture
from test import test_inventory_stock_execution_domain as execution_fixture
from test import test_inventory_stock_posting_domain as posting_fixture
from src.modules.inventory.domain.error import InventoryError, QuantityStepError
from src.modules.inventory.domain.inventory_count.error import (
    InventoryCountBaselineChangedError,
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
from src.modules.inventory.domain.inventory_item.document_snapshot import (
    InventoryItemDocumentSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.sku import SkuVO
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.error import (
    InventoryCountAdjustmentMismatchError,
    InvalidStockAdjustmentLineError,
    InvalidStockDocumentLineError,
    StockAdjustmentDocumentImmutableError,
    StockDocumentExecutionNotAllowedError,
)
from src.modules.inventory.domain.stock_document.value_object.adjustment_line import (
    StockAdjustmentLineVO,
)
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.identifier import (
    StockDocumentIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.inventory_count_line_binding import (
    InventoryCountDocumentLineBindingVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_source import (
    DocumentLineSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class InventoryCountAdjustmentDocumentDomainTests(unittest.TestCase):
    """Проверяет связь COUNTED → результат → документ и закрытый контур движения запасов."""

    def setUp(self) -> None:
        """Готовит зарегистрированный результат с недостачей 23, найденными 5 и известным нулём."""
        self.f = result_fixture.InventoryCountResultDomainTests()
        self.f.setUp()
        self.warehouse = self.f.f.f.warehouse
        self.f.sheets = (*self.f.sheets, self.f.found())
        self.time = self.f.time
        self.refresh()

    def refresh(self, **context: object) -> None:
        """Заново собирает и регистрирует результат через публичные правила предыдущего среза."""
        self.result = self.f.build(warehouse=self.warehouse, **context)
        self.count = self.f.register(self.result, warehouse=self.warehouse, **context)
        item = self.f.item
        self.item = InventoryItemDocumentSnapshot(
            item.inventory_item_id,
            SkuVO("COUNT"),
            item.base_uom,
            item.quantity_rules,
            item.tracking_mode,
        )
        self.extra = context

    def bindings(self) -> tuple[InventoryCountDocumentLineBindingVO, ...]:
        """Назначает ID только ненулевым наблюдениям по составному ключу."""
        return tuple(
            InventoryCountDocumentLineBindingVO(
                StockDocumentLineIdVO(uuid4()), row.sheet_id, row.observation.id
            )
            for row in self.result.lines
            if not row.discrepancy.value.is_zero()
        )

    def context(self) -> dict[str, object]:
        """Передаёт свежий снимок COUNTED и полные позиции области, включая неизменённые нули."""
        return (
            dict(
                inventory_count=self.count.adjustment_source_snapshot(),
                result=self.result,
                baseline=self.f.baseline,
                warehouse=self.warehouse,
                inventory_items=(self.item,),
                locations=self.f.baseline.locations,
                positions=self.f.baseline.positions,
            )
            | self.extra
        )

    def build(self, **changes: object) -> StockDocument | None:
        """Строит план без изменения родителя, ведомостей и физических позиций."""
        return StockDocument.create_from_inventory_count_result(
            **(
                self.context()
                | dict(
                    identifier=StockDocumentIdVO(uuid4()),
                    line_bindings=self.bindings(),
                    created_at=self.time,
                )
                | changes
            )
        )

    def confirm(self, document: StockDocument, **changes: object) -> StockDocument:
        """Повторно передаёт контекст основания перед подтверждением документа."""
        return document.confirm_inventory_count_adjustment(
            **(self.context() | dict(updated_at=self.time) | changes)
        )

    def restore(self, document: StockDocument, **changes: object) -> StockDocument:
        """Восстанавливает собственную историю документа без текущих остатков и результата."""
        values = {
            field.name: getattr(document, field.name) for field in fields(document)
        }
        values["identifier"] = values.pop("id")
        return StockDocument.restore(**(values | changes))

    def test_mixed_deltas_preserve_sources_and_do_not_move_stock(self) -> None:
        """Недостача и излишек остаются разными строками; известный ноль не попадает в документ."""
        before = (self.count, self.result, self.f.baseline, self.f.sheets)
        document = self.build()
        self.assertIsNotNone(document)
        self.assertEqual(document.operation_type, StockOperationType.ADJUSTMENT)
        self.assertEqual(document.status, StockDocumentStatus.DRAFT)
        self.assertEqual(document.version, 0)
        self.assertEqual(
            document.source,
            DocumentSourceVO("inventory_count_result", str(self.result.id.uuid)),
        )
        self.assertEqual(
            {line.adjustment.quantity_delta.value for line in document.lines},
            {Decimal(-23), Decimal(5)},
        )
        self.assertEqual(len(document.lines), 2)
        found = next(
            line for line in document.lines if line.adjustment.position_id is None
        )
        self.assertEqual(found.adjustment.expected_qty.value, 0)
        self.assertIsNone(found.adjustment.position_version)
        for line in document.lines:
            self.assertEqual(line.conversion.factor_to_base, 1)
            self.assertEqual(line.conversion.uom, line.base_uom)
            self.assertEqual(
                line.planned_qty.value, line.adjustment.quantity_delta.value.copy_abs()
            )
            self.assertEqual(line.executed_qty.value, 0)
            self.assertEqual(line.source.system, "inventory_count_result_line")
        confirmed = self.confirm(document)
        self.assertEqual(confirmed.status, StockDocumentStatus.CONFIRMED)
        self.assertEqual(confirmed.version, 1)
        self.assertEqual(
            before, (self.count, self.result, self.f.baseline, self.f.sheets)
        )
        self.assertEqual(self.count.status, InventoryCountStatus.COUNTED)
        self.assertEqual(self.f.baseline.positions[0].on_hand_qty.value, 100)

    def test_all_zero_returns_none_after_full_validation(self) -> None:
        """Совпавшие остатки не создают пустой документ, но требуют актуального полного основания."""
        self.f.sheets = (
            replace(
                self.f.first,
                lines=(
                    replace(
                        self.f.first.lines[0], counted_qty=QuantityVO(Decimal(100))
                    ),
                ),
            ),
            self.f.second,
        )
        self.refresh()
        self.assertIsNone(self.build(inventory_items=()))
        with self.assertRaises(InventoryCountBaselineChangedError):
            self.build(inventory_items=(), positions=self.f.baseline.positions[:1])
        with self.assertRaises(InventoryCountAdjustmentMismatchError):
            self.build()

    def test_found_only_empty_baseline_does_not_invent_stock_position(self) -> None:
        """Пустое основание с найденным товаром даёт приходную цель без фиктивной позиции."""
        dimensions = replace(
            self.f.baseline.positions[0].dimensions, stock_status=StockStatus.DAMAGED
        )
        self.f.baseline = replace(self.f.baseline, positions=())
        self.f.sheets = (self.f.found(dimensions=dimensions),)
        self.refresh()
        document = self.build()
        self.assertEqual(len(document.lines), 1)
        details = document.lines[0].adjustment
        self.assertIsNone(details.position_id)
        self.assertIsNone(details.position_version)
        self.assertEqual(details.quantity_delta.value, 5)
        self.confirm(document)
        self.assertEqual(self.f.baseline.positions, ())

    def test_known_zero_is_distinct_from_found(self) -> None:
        """Положительная поправка известного нуля сохраняет его ID и реальную версию ноль."""
        self.f.sheets = (
            replace(
                self.f.first,
                lines=(
                    replace(
                        self.f.first.lines[0], counted_qty=QuantityVO(Decimal(100))
                    ),
                ),
            ),
            replace(
                self.f.second,
                lines=(
                    replace(self.f.second.lines[0], counted_qty=QuantityVO(Decimal(2))),
                ),
            ),
        )
        self.refresh()
        document = self.build()
        self.assertEqual(len(document.lines), 1)
        details = document.lines[0].adjustment
        self.assertEqual(details.position_id, self.f.baseline.positions[1].id)
        self.assertEqual(details.position_version, 0)
        self.assertEqual(details.expected_qty.value, 0)
        self.assertEqual(details.target_qty.value, 2)
        self.confirm(document)

    def test_current_parent_and_registered_result_are_required(self) -> None:
        """IN_PROGRESS, чужой результат, неверная версия и хронология не служат основанием."""
        source = self.count.adjustment_source_snapshot()
        for changed in (
            replace(source, status=InventoryCountStatus.IN_PROGRESS, result=None),
            replace(
                source,
                result=InventoryCountResultRefVO(
                    InventoryCountResultIdVO(uuid4()), self.result.prepared_at
                ),
            ),
            replace(source, version=self.result.inventory_count_version),
            replace(source, owner_id=self.f.f.f.owner.__class__(uuid4())),
        ):
            with self.subTest(source=changed), self.assertRaises(InventoryError):
                self.build(inventory_count=changed)
        with self.assertRaises(InventoryError):
            self.build(created_at=self.time - timedelta(seconds=1))

    def test_source_snapshot_has_both_refs_and_strict_validation(self) -> None:
        """Снимок сохраняет две ссылки и версию родителя, не вводя версию immutable результата."""
        source = self.count.adjustment_source_snapshot()
        self.assertEqual(source.baseline, self.count.baseline)
        self.assertEqual(source.result, self.count.result)
        self.assertLess(self.result.inventory_count_version, source.version)
        for changes in (
            dict(version=True),
            dict(result=None),
            dict(result="result"),
            dict(updated_at=self.time.replace(tzinfo=None)),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                replace(source, **changes).ensure_valid()
        with self.assertRaises(FrozenInstanceError):
            source.version = 4

    def test_bindings_must_cover_exactly_nonzero_rows_once(self) -> None:
        """Отклоняет пропуски, лишние нулевые строки и повтор любых назначенных ID."""
        bindings = self.bindings()
        zero = next(row for row in self.result.lines if row.discrepancy.value.is_zero())
        extra = InventoryCountDocumentLineBindingVO(
            StockDocumentLineIdVO(uuid4()), zero.sheet_id, zero.observation.id
        )
        for values in (
            (),
            bindings[:1],
            (*bindings, extra),
            (*bindings, bindings[0]),
            (
                bindings[0],
                replace(bindings[1], document_line_id=bindings[0].document_line_id),
            ),
            list(bindings),
            (None,),
        ):
            with self.subTest(bindings=values), self.assertRaises(InventoryError):
                self.build(line_bindings=values)

    def test_observation_ids_are_local_to_each_sheet(self) -> None:
        """Одинаковый CountLineId в разных ведомостях различается составным источником."""
        first = self.f.sheets[0]
        found = self.f.sheets[2]
        self.f.sheets = (
            first,
            self.f.sheets[1],
            replace(found, lines=(replace(found.lines[0], id=first.lines[0].id),)),
        )
        self.refresh()
        document = self.build()
        self.assertEqual(len(document.lines), 2)
        self.assertEqual(len({line.source.reference for line in document.lines}), 2)
        self.confirm(document)

    def test_baseline_changes_block_creation_and_confirmation(self) -> None:
        """Изменение версии/количества, новая позиция или адрес требуют нового учётного основания."""
        document = self.build()
        positions = self.f.baseline.positions
        changed_sets = (
            positions[:1],
            (replace(positions[0], version=positions[0].version + 1), positions[1]),
            (positions[0], replace(positions[1], on_hand_qty=QuantityVO(Decimal(1)))),
            (
                *positions,
                replace(
                    positions[1],
                    id=StockPositionIdVO(uuid4()),
                    dimensions=replace(
                        positions[1].dimensions, stock_status=StockStatus.DAMAGED
                    ),
                ),
            ),
        )
        for changed in changed_sets:
            with self.subTest(positions=changed):
                with self.assertRaises(InventoryCountBaselineChangedError):
                    self.build(positions=changed)
                with self.assertRaises(InventoryCountBaselineChangedError):
                    self.confirm(document, positions=changed)
        extra = replace(
            self.f.baseline.locations[0],
            id=self.f.baseline.locations[0].id.__class__(uuid4()),
        )
        with self.assertRaises(InventoryCountBaselineChangedError):
            self.confirm(document, locations=(*self.f.baseline.locations, extra))

    def test_historical_baseline_rows_cannot_be_forged_or_omitted(self) -> None:
        """Даже нулевая строка результата обязана совпасть с полным сохранённым основанием."""
        result = self.result
        zero = next(
            row
            for row in result.lines
            if row.observation.position_id is not None
            and row.discrepancy.value.is_zero()
        )
        changed = replace(
            zero, observation=replace(zero.observation, position_version=9)
        )
        for value in (
            replace(
                result,
                lines=tuple(changed if row == zero else row for row in result.lines),
            ),
            replace(result, lines=tuple(row for row in result.lines if row != zero)),
        ):
            with self.subTest(result=value), self.assertRaises(InventoryError):
                self.build(result=value)

    def test_manual_editing_is_forbidden_even_in_draft(self) -> None:
        """Нельзя добавить, изменить или удалить строку производного черновика."""
        document = self.build()
        line = document.lines[0]
        with self.assertRaises(StockAdjustmentDocumentImmutableError):
            document.add_line(line, inventory_item=self.item, updated_at=self.time)
        with self.assertRaises(StockAdjustmentDocumentImmutableError):
            document.change_line(
                identifier=line.id,
                quantity=QuantityVO(Decimal(1)),
                uom=self.item.base_uom,
                inventory_item=self.item,
                updated_at=self.time,
            )
        with self.assertRaises(StockAdjustmentDocumentImmutableError):
            document.remove_line(line.id, updated_at=self.time)

    def test_confirm_requires_full_fresh_source(self) -> None:
        """Общее подтверждение без COUNTED, результата и полного основания запрещено."""
        document = self.build()
        with self.assertRaises(InventoryCountAdjustmentMismatchError):
            document.confirm(
                warehouse=self.warehouse,
                inventory_items=(self.item,),
                updated_at=self.time,
            )
        for key in ("inventory_count", "result", "baseline", "locations", "positions"):
            with self.subTest(missing=key), self.assertRaises(InventoryError):
                self.confirm(document, **{key: None})

    def test_tampered_delta_and_target_are_rejected_before_confirm(self) -> None:
        """Собственно корректная строка с другой целью не может подтвердиться по исходному результату."""
        document = self.build()
        original = next(
            line for line in document.lines if line.adjustment.quantity_delta.value < 0
        )
        changed = StockDocumentLine.create_adjustment(
            identifier=original.id,
            inventory_item=self.item,
            adjustment=replace(original.adjustment, target_qty=QuantityVO(Decimal(76))),
            source=original.source,
        )
        restored = self.restore(
            document,
            lines=tuple(
                changed if line.id == original.id else line for line in document.lines
            ),
        )
        with self.assertRaises(InventoryCountAdjustmentMismatchError):
            self.confirm(restored)
        opposite = StockDocumentLine.create_adjustment(
            identifier=original.id,
            inventory_item=self.item,
            adjustment=replace(
                original.adjustment, target_qty=QuantityVO(Decimal(123))
            ),
            source=original.source,
        )
        self.assertEqual(opposite.planned_qty, original.planned_qty)
        with self.assertRaises(InventoryCountAdjustmentMismatchError):
            self.confirm(
                self.restore(
                    document,
                    lines=tuple(
                        opposite if line.id == original.id else line
                        for line in document.lines
                    ),
                )
            )

    def test_tampered_position_and_dimensions_are_rejected_before_confirm(self) -> None:
        """Другие версия позиции, источник или физические измерения не заменяют исходную строку."""
        document = self.build()
        original = next(
            line for line in document.lines if line.adjustment.position_id is not None
        )
        variants = (
            replace(
                original, adjustment=replace(original.adjustment, position_version=99)
            ),
            replace(
                original,
                adjustment=replace(
                    original.adjustment,
                    dimensions=replace(
                        original.adjustment.dimensions, stock_status=StockStatus.BLOCKED
                    ),
                ),
            ),
            replace(
                original,
                source=DocumentLineSourceVO(
                    "inventory_count_result_line", f"{uuid4()}:{uuid4()}"
                ),
            ),
        )
        for changed in variants:
            with self.subTest(line=changed), self.assertRaises(InventoryError):
                self.confirm(
                    self.restore(
                        document,
                        lines=tuple(
                            changed if line.id == original.id else line
                            for line in document.lines
                        ),
                    )
                )

    def test_restore_checks_reserved_source_and_metadata(self) -> None:
        """История восстанавливается без свежего контекста, но требует строгие собственные инварианты."""
        document = self.build()
        self.assertEqual(self.restore(document), document)
        for changes in (
            dict(source=None),
            dict(source=replace(document.source, version=1)),
            dict(source=replace(document.source, reference="wrong")),
            dict(lines=()),
            dict(operation_type=StockOperationType.RECEIPT),
            dict(status=StockDocumentStatus.PARTIALLY_EXECUTED),
            dict(status=StockDocumentStatus.COMPLETED),
            dict(lines=(replace(document.lines[0], adjustment=None),)),
            dict(
                lines=(
                    replace(
                        document.lines[0],
                        source=DocumentLineSourceVO(
                            "inventory_count_result_line", str(uuid4())
                        ),
                    ),
                )
            ),
        ):
            with self.subTest(changes=changes), self.assertRaises(InventoryError):
                self.restore(document, **changes)
        with self.assertRaises(InventoryCountAdjustmentMismatchError):
            StockDocument.create(
                identifier=StockDocumentIdVO(uuid4()),
                operation_type=StockOperationType.ADJUSTMENT,
                warehouse=self.warehouse,
                owner_id=self.count.owner_id,
                created_at=self.time,
            )

    def test_adjustment_metadata_cannot_bypass_ordinary_document_rules(self) -> None:
        """Обычный документ не принимает корректировку даже с универсальными внешними ссылками."""
        document = self.build()
        line = replace(document.lines[0], source=None)
        with self.assertRaises(InventoryCountAdjustmentMismatchError):
            self.restore(
                document,
                operation_type=StockOperationType.RECEIPT,
                source=None,
                lines=(line,),
            )

    def test_snapshot_source_cannot_be_reused_for_another_document(self) -> None:
        """Подтверждение проверяет ID результата и шапку документа, даже когда строки совпали."""
        document = self.build()
        other = self.restore(
            document, source=DocumentSourceVO("inventory_count_result", str(uuid4()))
        )
        with self.assertRaises(InventoryCountAdjustmentMismatchError):
            self.confirm(other)

    def test_cancel_preserves_basis_in_draft_and_confirmed(self) -> None:
        """Отмена плана сохраняет строки и не изменяет COUNTED-родителя."""
        document = self.build()
        for value in (document, self.confirm(document)):
            cancelled = value.cancel(updated_at=self.time)
            self.assertEqual(cancelled.status, StockDocumentStatus.CANCELLED)
            self.assertEqual(cancelled.lines, value.lines)
            self.assertEqual(self.restore(cancelled), cancelled)

    def test_sku_change_does_not_rewrite_historical_sku(self) -> None:
        """Подтверждение по текущей карточке сохраняет SKU, зафиксированный при создании."""
        document = self.build()
        changed = replace(self.item, sku=SkuVO("NEW"))
        confirmed = self.confirm(document, inventory_items=(changed,))
        self.assertTrue(all(line.sku == self.item.sku for line in confirmed.lines))

    def test_current_item_set_and_base_uom_are_strict(self) -> None:
        """Лишние/повторные карточки, иной шаг цели или смена базовой единицы запрещены."""
        document = self.build()
        for items in (
            (),
            (self.item, self.item),
            (replace(self.item, base_uom=UomCodeVO("KG")),),
            (replace(self.item, quantity_rules=QuantityRulesVO(Decimal(2))),),
        ):
            with self.subTest(items=items), self.assertRaises(InventoryError):
                self.confirm(document, inventory_items=items)

    def test_inactive_warehouse_blocks_but_inactive_physical_location_is_preserved(
        self,
    ) -> None:
        """Для подтверждения нужен активный склад; физический адрес пересчёта не фильтруется по активности."""
        document = self.build()
        locations = tuple(
            replace(location, is_active=False) for location in self.f.baseline.locations
        )
        self.confirm(document, locations=locations)
        with self.assertRaises(InventoryError):
            self.confirm(document, warehouse=replace(self.warehouse, is_active=False))

    def test_ordinary_execution_projection_and_registration_are_closed(self) -> None:
        """Корректировка не публикует неполный снимок для обычного маршрута исполнения."""
        document = self.confirm(self.build())
        with self.assertRaises(StockDocumentExecutionNotAllowedError):
            document.execution_snapshot()
        with self.assertRaises(StockDocumentExecutionNotAllowedError):
            document.register_execution(None, updated_at=self.time)

    def test_raw_factories_stay_closed_but_posting_history_can_restore_adjustment(
        self,
    ) -> None:
        """Общие фабрики не включают корректировку; restore сохраняет собственную историю проведения."""
        f = execution_fixture.StockExecutionDomainTests()
        f.setUp()
        execution = f.create()
        unsupported = replace(
            f.document.execution_snapshot(),
            operation_type=StockOperationType.ADJUSTMENT,
        )
        with self.assertRaises(InventoryError):
            unsupported.ensure_valid()
        with self.assertRaises(InventoryError):
            f.create(document=unsupported)
        values = {
            field.name: getattr(execution, field.name) for field in fields(execution)
        }
        values["identifier"] = values.pop("id")
        with self.assertRaises(InventoryError):
            StockExecution.restore(
                **(values | dict(operation_type=StockOperationType.ADJUSTMENT))
            )
        p = posting_fixture.StockPostingDomainTests()
        p.setUp()
        with self.assertRaises(InventoryError):
            p.posting(operation_type=StockOperationType.ADJUSTMENT)
        posting = p.posting()
        saved = {field.name: getattr(posting, field.name) for field in fields(posting)}
        saved["identifier"] = saved.pop("id")
        restored = StockPosting.restore(
            **(saved | dict(operation_type=StockOperationType.ADJUSTMENT))
        )
        self.assertEqual(restored.operation_type, StockOperationType.ADJUSTMENT)

    def test_adjustment_value_requires_nonzero_delta_and_paired_position(self) -> None:
        """Нулевая разница, отрицательная/булева версия и фиктивное основание найденного запаса недопустимы."""
        value = self.build().lines[0].adjustment
        for changes in (
            dict(target_qty=value.expected_qty),
            dict(position_id=None, position_version=1),
            dict(position_id=StockPositionIdVO(uuid4()), position_version=None),
            dict(position_id=StockPositionIdVO(uuid4()), position_version=True),
            dict(position_id=StockPositionIdVO(uuid4()), position_version=-1),
            dict(
                position_id=None,
                position_version=None,
                expected_qty=QuantityVO(Decimal(1)),
            ),
            dict(target_qty=Decimal(1)),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidStockAdjustmentLineError),
            ):
                replace(value, **changes)

    def test_legacy_quantity_uses_current_step_only_for_target(self) -> None:
        """100.1 KG при шаге 0.2 исправляется до 100.2 точной дельтой +0.1 без округления."""
        self.f.sheets = self.f.sheets[:2]
        self.f.item = replace(
            self.f.item,
            base_uom=UomCodeVO("KG"),
            quantity_rules=QuantityRulesVO(Decimal("0.2")),
        )
        positions = tuple(
            replace(
                position,
                base_uom=UomCodeVO("KG"),
                on_hand_qty=QuantityVO(Decimal("100.1") if index == 0 else Decimal(0)),
            )
            for index, position in enumerate(self.f.baseline.positions)
        )
        self.f.baseline = replace(self.f.baseline, positions=positions)
        sheets = []
        for sheet in self.f.sheets:
            original = sheet.lines[0]
            first = original.position_id == positions[0].id
            sheets.append(
                replace(
                    sheet,
                    lines=(
                        replace(
                            original,
                            base_uom=UomCodeVO("KG"),
                            expected_qty=QuantityVO(
                                Decimal("100.1") if first else Decimal(0)
                            ),
                            counted_qty=QuantityVO(
                                Decimal("100.2") if first else Decimal(0)
                            ),
                        ),
                    ),
                )
            )
        self.f.sheets = tuple(sheets)
        self.refresh()
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = context.traps[Rounded] = True
            document = self.build()
            self.assertEqual(
                document.lines[0].adjustment.quantity_delta.value, Decimal("0.1")
            )
            self.assertEqual(document.lines[0].planned_qty.value, Decimal("0.1"))
            self.confirm(document)
        with self.assertRaises(QuantityStepError):
            StockDocumentLine.create(
                identifier=StockDocumentLineIdVO(uuid4()),
                inventory_item=self.item,
                quantity=QuantityVO(Decimal("0.1")),
                uom=self.item.base_uom,
            )

    def test_serial_zero_or_one_is_preserved_and_current_identity_rechecked(
        self,
    ) -> None:
        """Недостача SERIAL 1 → 0 остаётся единичной; отсутствие или чужая серия блокируют подтверждение."""
        serial = self.f.serial_sources("0")
        self.refresh()
        self.extra = dict(serials=(serial,))
        document = self.build()
        self.assertEqual(len(document.lines), 1)
        self.assertEqual(document.lines[0].adjustment.quantity_delta.value, -1)
        self.confirm(document)
        with self.assertRaises(InventoryError):
            self.confirm(document, serials=())
        details = document.lines[0].adjustment
        with self.assertRaises(InvalidStockAdjustmentLineError):
            replace(details, target_qty=QuantityVO(Decimal(2)))

    def test_serial_relocation_remains_two_adjustment_lines(self) -> None:
        """SERIAL 1 → 0 в A и FOUND 0 → 1 в B не исчезают при нулевом общем итоге."""
        serial = self.f.serial_sources("0")
        self.f.sheets = (*self.f.sheets, self.f.found(quantity="1", serial=serial))
        self.refresh(serials=(serial,))
        document = self.build()
        self.assertEqual(len(document.lines), 2)
        self.assertEqual(
            {line.adjustment.quantity_delta.value for line in document.lines},
            {Decimal(-1), Decimal(1)},
        )
        self.confirm(document)

    def test_adjustment_line_rejects_execution_or_nonbase_conversion(self) -> None:
        """Локальное восстановление не допускает исполнение или иной пересчёт корректировки."""
        original = self.build().lines[0]
        for changed in (
            replace(original, executed_qty=QuantityVO(Decimal(1))),
            replace(
                original,
                conversion=QuantityConversionSnapshotVO(
                    original.planned_qty, original.base_uom, Decimal(2)
                ),
            ),
            replace(original, planned_qty=QuantityVO(Decimal(1))),
        ):
            with self.subTest(line=changed), self.assertRaises(InventoryError):
                changed.ensure_valid()

    def test_lot_and_status_corrections_are_not_netted(self) -> None:
        """Две партии и состояния сохраняют самостоятельные знаковые строки и текущую принадлежность партий."""
        self.f.sheets = self.f.sheets[:2]
        self.f.item = replace(self.f.item, tracking_mode=TrackingMode.LOT)
        lots = tuple(
            StockLotSnapshot(
                StockLotIdVO(uuid4()), self.f.item.inventory_item_id, StockDatesVO()
            )
            for _ in range(2)
        )
        positions = tuple(
            replace(
                position, dimensions=replace(position.dimensions, lot_id=lots[index].id)
            )
            for index, position in enumerate(self.f.baseline.positions)
        )
        self.f.baseline = replace(self.f.baseline, positions=positions)
        self.f.sheets = tuple(
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
            for index, sheet in enumerate(self.f.sheets)
        )
        self.refresh()
        document = self.build(lots=lots)
        self.assertEqual(
            {line.adjustment.quantity_delta.value for line in document.lines},
            {Decimal(-23), Decimal(23)},
        )
        self.assertEqual(
            {line.adjustment.dimensions.lot_id for line in document.lines},
            {lot.id for lot in lots},
        )
        self.confirm(document, lots=lots)
        with self.assertRaises(InventoryError):
            self.confirm(document, lots=lots[:1])
        with self.assertRaises(InventoryError):
            self.confirm(
                document,
                lots=(
                    lots[0],
                    replace(
                        lots[1],
                        inventory_item_id=lots[1].inventory_item_id.__class__(uuid4()),
                    ),
                ),
            )


if __name__ == "__main__":
    unittest.main()
