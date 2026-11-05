from dataclasses import replace
from datetime import datetime
from uuid import UUID

from src.modules.inventory.domain.count_sheet.value_object.identifier import (
    CountSheetIdVO,
)
from src.modules.inventory.domain.count_sheet.value_object.line_id import CountLineIdVO
from src.modules.inventory.domain.count_sheet.value_object.line_origin import (
    CountLineOrigin,
)
from src.modules.inventory.domain.inventory_count.adjustment_source_snapshot import (
    InventoryCountAdjustmentSourceSnapshot,
)
from src.modules.inventory.domain.inventory_count.baseline_snapshot import (
    InventoryCountBaselineSnapshot,
)
from src.modules.inventory.domain.inventory_count.result_snapshot import (
    InventoryCountResultSnapshot,
)
from src.modules.inventory.domain.inventory_count.time import (
    normalize_inventory_count_time,
)
from src.modules.inventory.domain.inventory_count.value_object.baseline_ref import (
    InventoryCountBaselineRefVO,
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
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.found_count_line import FoundCountLinePolicy
from src.modules.inventory.domain.policy.inventory_count_baseline import (
    InventoryCountBaselinePolicy,
)
from src.modules.inventory.domain.policy.stock_dimensions import StockDimensionsPolicy
from src.modules.inventory.domain.policy.stock_document_confirmation import (
    StockDocumentConfirmationPolicy,
)
from src.modules.inventory.domain.stock_document.entity.stock_document_line import (
    StockDocumentLine,
)
from src.modules.inventory.domain.stock_document.error import (
    InventoryCountAdjustmentMismatchError,
)
from src.modules.inventory.domain.stock_document.value_object.adjustment_line import (
    StockAdjustmentLineVO,
)
from src.modules.inventory.domain.stock_document.value_object.document_source import (
    DocumentSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.inventory_count_line_binding import (
    InventoryCountDocumentLineBindingVO,
)
from src.modules.inventory.domain.stock_document.value_object.line_source import (
    DocumentLineSourceVO,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


class InventoryCountAdjustmentDocumentPolicy:
    """Строит точные корректировки зарегистрированного результата и повторно проверяет всё учётное основание."""

    SOURCE_SYSTEM = "inventory_count_result"
    LINE_SOURCE_SYSTEM = "inventory_count_result_line"

    @staticmethod
    def line_binding(line: StockDocumentLine) -> InventoryCountDocumentLineBindingVO:
        """Разбирает строго составное основание ведомость/строка, не считая ID наблюдения глобальным."""
        if not isinstance(line, StockDocumentLine):
            raise InventoryCountAdjustmentMismatchError(
                "Нужна типизированная строка документа."
            )
        line.ensure_valid()
        if (
            line.source is None
            or line.source.system
            != InventoryCountAdjustmentDocumentPolicy.LINE_SOURCE_SYSTEM
        ):
            raise InventoryCountAdjustmentMismatchError(
                "Строка корректировки требует ссылку на исходное наблюдение."
            )
        parts = line.source.reference.split(":")
        if len(parts) != 2:
            raise InventoryCountAdjustmentMismatchError(
                "Нужен составной источник ведомость:строка."
            )
        try:
            sheet, observation = UUID(parts[0]), UUID(parts[1])
        except (ValueError, TypeError, AttributeError) as exc:
            raise InventoryCountAdjustmentMismatchError(
                "Основание строки должно содержать UUID."
            ) from exc
        if parts != [str(sheet), str(observation)]:
            raise InventoryCountAdjustmentMismatchError(
                "UUID основания должны быть в каноническом формате."
            )
        return InventoryCountDocumentLineBindingVO(
            line.id, CountSheetIdVO(sheet), CountLineIdVO(observation)
        )

    @staticmethod
    def ensure_document_source(
        *,
        operation_type: StockOperationType,
        source: DocumentSourceVO | None,
        owner_id: StockOwnerIdVO,
        status: StockDocumentStatus,
        lines: tuple[StockDocumentLine, ...],
    ) -> None:
        """Проверяет собственный состав и закрывает исполнение, сохраняя восстановление истории без свежих снимков."""
        adjustment = operation_type is StockOperationType.ADJUSTMENT
        if not adjustment:
            if (
                source is not None
                and source.system
                in (
                    InventoryCountAdjustmentDocumentPolicy.SOURCE_SYSTEM,
                    InventoryCountAdjustmentDocumentPolicy.LINE_SOURCE_SYSTEM,
                )
            ) or any(
                line.adjustment is not None
                or (
                    line.source is not None
                    and line.source.system
                    in (
                        InventoryCountAdjustmentDocumentPolicy.SOURCE_SYSTEM,
                        InventoryCountAdjustmentDocumentPolicy.LINE_SOURCE_SYSTEM,
                    )
                )
                for line in lines
            ):
                raise InventoryCountAdjustmentMismatchError(
                    "Основания пересчёта и физическая корректировка допустимы только в ADJUSTMENT."
                )
            return
        if (
            source is None
            or source.system != InventoryCountAdjustmentDocumentPolicy.SOURCE_SYSTEM
            or source.version is not None
            or not lines
            or status
            not in (
                StockDocumentStatus.DRAFT,
                StockDocumentStatus.CONFIRMED,
                StockDocumentStatus.CANCELLED,
                StockDocumentStatus.COMPLETED,
            )
        ):
            raise InventoryCountAdjustmentMismatchError(
                "ADJUSTMENT требует неизменяемый результат без собственной версии, строки и состояние без частичного исполнения."
            )
        try:
            source_id = UUID(source.reference)
        except (ValueError, TypeError, AttributeError) as exc:
            raise InventoryCountAdjustmentMismatchError(
                "Нужен UUID результата."
            ) from exc
        if source.reference != str(source_id):
            raise InventoryCountAdjustmentMismatchError(
                "UUID результата должен быть каноническим."
            )
        sources, dimensions, positions = set(), set(), set()
        serial_identity, serial_positive = {}, set()
        for line in lines:
            line.ensure_valid()
            binding = InventoryCountAdjustmentDocumentPolicy.line_binding(line)
            key = (binding.sheet_id, binding.count_line_id)
            details = line.adjustment
            if (
                details is None
                or details.dimensions.owner_id != owner_id
                or key in sources
                or details.dimensions in dimensions
                or (
                    details.position_id is not None and details.position_id in positions
                )
            ):
                raise InventoryCountAdjustmentMismatchError(
                    "Каждое ненулевое наблюдение, позиция и измерения должны входить один раз для владельца документа."
                )
            sources.add(key)
            dimensions.add(details.dimensions)
            if details.position_id is not None:
                positions.add(details.position_id)
            serial_id = details.dimensions.serial_id
            if serial_id is not None:
                identity = (
                    line.inventory_item_id,
                    details.dimensions.lot_id,
                    line.base_uom,
                )
                if (
                    serial_id in serial_identity
                    and serial_identity[serial_id] != identity
                ) or (
                    not details.target_qty.value.is_zero()
                    and serial_id in serial_positive
                ):
                    raise InventoryCountAdjustmentMismatchError(
                        "SERIAL требует единую идентичность и не более одной положительной цели в документе."
                    )
                serial_identity[serial_id] = identity
                if not details.target_qty.value.is_zero():
                    serial_positive.add(serial_id)

    @staticmethod
    def build_lines(
        *,
        inventory_count: InventoryCountAdjustmentSourceSnapshot,
        result: InventoryCountResultSnapshot,
        baseline: InventoryCountBaselineSnapshot,
        warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemDocumentSnapshot, ...],
        line_bindings: tuple[InventoryCountDocumentLineBindingVO, ...],
        locations: tuple[StockLocationSnapshot, ...],
        positions: tuple[StockPositionCountingSnapshot, ...],
        as_of: datetime,
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialSnapshot, ...] = (),
    ) -> tuple[StockDocumentLine, ...]:
        """Включает все ненулевые разницы без сальдирования, возвращая пустой состав только после проверки всего основания."""
        if (
            not isinstance(inventory_count, InventoryCountAdjustmentSourceSnapshot)
            or not isinstance(result, InventoryCountResultSnapshot)
            or not isinstance(baseline, InventoryCountBaselineSnapshot)
        ):
            raise InventoryCountAdjustmentMismatchError(
                "Нужны текущий родитель, зарегистрированный результат и полное основание."
            )
        inventory_count.ensure_valid()
        result.ensure_valid()
        baseline.ensure_valid()
        checked = normalize_inventory_count_time(as_of)
        if (
            inventory_count.status is not InventoryCountStatus.COUNTED
            or inventory_count.result
            != InventoryCountResultRefVO(result.id, result.prepared_at)
            or inventory_count.baseline != result.baseline
            or result.baseline
            != InventoryCountBaselineRefVO(baseline.id, baseline.snapshot_at)
            or result.inventory_count_id != inventory_count.id
            or baseline.inventory_count_id != inventory_count.id
            or result.warehouse_id != inventory_count.warehouse_id
            or baseline.warehouse_id != inventory_count.warehouse_id
            or result.owner_id != inventory_count.owner_id
            or baseline.owner_id != inventory_count.owner_id
            or result.scope != inventory_count.scope
            or baseline.scope != inventory_count.scope
            or not baseline.inventory_count_version
            < result.inventory_count_version
            < inventory_count.version
            or checked < inventory_count.updated_at
        ):
            raise InventoryCountAdjustmentMismatchError(
                "Результат не соответствует COUNTED-родителю, его ссылкам, области, версии или хронологии."
            )
        StockDocumentConfirmationPolicy.ensure_warehouse(
            warehouse_id=inventory_count.warehouse_id, warehouse=warehouse
        )
        InventoryCountBaselinePolicy.ensure_unchanged(
            baseline=baseline, locations=locations, positions=positions
        )
        known = {position.id: position for position in baseline.positions}
        covered = set()
        for row in result.lines:
            line = row.observation.as_line()
            if line.origin is CountLineOrigin.BASELINE:
                if known.get(line.position_id) != line.baseline_position_snapshot():
                    raise InventoryCountAdjustmentMismatchError(
                        "Исторические измерения, количество или версия строки изменены относительно основания."
                    )
                covered.add(line.position_id)
            else:
                FoundCountLinePolicy.ensure_sources(lines=(line,), baseline=baseline)
        if covered != set(known):
            raise InventoryCountAdjustmentMismatchError(
                "Результат должен полностью покрывать основание, включая нулевые строки."
            )
        rows = {
            (row.sheet_id, row.observation.id): row
            for row in result.lines
            if not row.discrepancy.value.is_zero()
        }
        if (
            not isinstance(line_bindings, tuple)
            or not isinstance(inventory_items, tuple)
            or not isinstance(lots, tuple)
            or not isinstance(serials, tuple)
        ):
            raise InventoryCountAdjustmentMismatchError(
                "Связи и текущий контекст передаются в tuple."
            )
        bindings, identifiers = {}, set()
        for binding in line_bindings:
            if not isinstance(binding, InventoryCountDocumentLineBindingVO):
                raise InventoryCountAdjustmentMismatchError(
                    "Нужны типизированные связи строк результата и документа."
                )
            key = (binding.sheet_id, binding.count_line_id)
            if key in bindings or binding.document_line_id in identifiers:
                raise InventoryCountAdjustmentMismatchError(
                    "Источники и новые ID строк не должны повторяться."
                )
            bindings[key] = binding
            identifiers.add(binding.document_line_id)
        if set(bindings) != set(rows):
            raise InventoryCountAdjustmentMismatchError(
                "Нужно назначить ID ровно всем ненулевым строкам результата."
            )
        by_item = {}
        for item in inventory_items:
            if not isinstance(item, InventoryItemDocumentSnapshot):
                raise InventoryCountAdjustmentMismatchError(
                    "Нужны снимки товаров документа."
                )
            item.ensure_valid()
            if item.inventory_item_id in by_item:
                raise InventoryCountAdjustmentMismatchError(
                    "Снимок товара повторяется."
                )
            by_item[item.inventory_item_id] = item
        if set(by_item) != {
            row.observation.dimensions.inventory_item_id for row in rows.values()
        }:
            raise InventoryCountAdjustmentMismatchError(
                "Нужны ровно товары ненулевых корректировок."
            )
        if any(
            not isinstance(lot, StockLotSnapshot)
            or not isinstance(lot.id, StockLotIdVO)
            or not isinstance(lot.inventory_item_id, InventoryItemIdVO)
            or not isinstance(lot.dates, StockDatesVO)
            for lot in lots
        ) or any(not isinstance(serial, StockSerialSnapshot) for serial in serials):
            raise InventoryCountAdjustmentMismatchError(
                "Нужны типизированные снимки партий и серий."
            )
        for serial in serials:
            serial.ensure_valid()
        by_lot = {lot.id: lot for lot in lots}
        by_serial = {serial.id: serial for serial in serials}
        if (
            len(by_lot) != len(lots)
            or len(by_serial) != len(serials)
            or set(by_lot)
            != {
                row.observation.dimensions.lot_id
                for row in rows.values()
                if row.observation.dimensions.lot_id is not None
            }
            or set(by_serial)
            != {
                row.observation.dimensions.serial_id
                for row in rows.values()
                if row.observation.dimensions.serial_id is not None
            }
        ):
            raise InventoryCountAdjustmentMismatchError(
                "Нужны ровно по одному снимку каждой партии и серии ненулевых строк."
            )
        by_location = {location.id: location for location in locations}
        lines = []
        for key, row in rows.items():
            observation = row.observation
            dimensions = observation.dimensions
            item = by_item[dimensions.inventory_item_id]
            location = by_location.get(dimensions.location_id)
            if location is None or observation.base_uom != item.base_uom:
                raise InventoryCountAdjustmentMismatchError(
                    "Нельзя менять адрес или базовую единицу исходного наблюдения."
                )
            StockDimensionsPolicy.ensure_compatible(
                dimensions=dimensions,
                inventory_item=InventoryItemStockSnapshot(
                    item.inventory_item_id,
                    item.base_uom,
                    item.quantity_rules,
                    item.tracking_mode,
                ),
                location=location,
                warehouse=warehouse,
                lot=by_lot.get(dimensions.lot_id),
                serial=by_serial.get(dimensions.serial_id),
            )
            lines.append(
                StockDocumentLine.create_adjustment(
                    identifier=bindings[key].document_line_id,
                    inventory_item=item,
                    adjustment=StockAdjustmentLineVO(
                        dimensions,
                        observation.position_id,
                        observation.position_version,
                        observation.expected_qty,
                        observation.counted_qty,
                    ),
                    source=DocumentLineSourceVO(
                        InventoryCountAdjustmentDocumentPolicy.LINE_SOURCE_SYSTEM,
                        f"{key[0].uuid}:{key[1].uuid}",
                    ),
                )
            )
        return tuple(lines)

    @staticmethod
    def ensure_confirmable(
        *,
        source: DocumentSourceVO,
        warehouse_id: WarehouseIdVO,
        owner_id: StockOwnerIdVO,
        lines: tuple[StockDocumentLine, ...],
        inventory_count: InventoryCountAdjustmentSourceSnapshot,
        result: InventoryCountResultSnapshot,
        baseline: InventoryCountBaselineSnapshot,
        warehouse: WarehouseSnapshot,
        inventory_items: tuple[InventoryItemDocumentSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        positions: tuple[StockPositionCountingSnapshot, ...],
        as_of: datetime,
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialSnapshot, ...] = (),
    ) -> None:
        """Повторно строит весь состав по свежему основанию, сохраняя исторический SKU документа."""
        expected = InventoryCountAdjustmentDocumentPolicy.build_lines(
            inventory_count=inventory_count,
            result=result,
            baseline=baseline,
            warehouse=warehouse,
            inventory_items=inventory_items,
            line_bindings=tuple(
                InventoryCountAdjustmentDocumentPolicy.line_binding(line)
                for line in lines
            ),
            locations=locations,
            positions=positions,
            as_of=as_of,
            lots=lots,
            serials=serials,
        )
        if (
            source
            != DocumentSourceVO(
                InventoryCountAdjustmentDocumentPolicy.SOURCE_SYSTEM,
                str(result.id.uuid),
            )
            or warehouse_id != result.warehouse_id
            or owner_id != result.owner_id
        ):
            raise InventoryCountAdjustmentMismatchError(
                "Заголовок документа не соответствует результату."
            )
        actual = {line.id: line for line in lines}
        if len(expected) != len(lines) or any(
            replace(line, sku=actual[line.id].sku) != actual[line.id]
            for line in expected
        ):
            raise InventoryCountAdjustmentMismatchError(
                "Знак, цель, основание, измерения или состав корректировки изменены."
            )
