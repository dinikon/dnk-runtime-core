from datetime import datetime

from src.modules.inventory.domain.count_sheet.reconciliation_snapshot import (
    CountSheetReconciliationSnapshot,
)
from src.modules.inventory.domain.count_sheet.value_object.line_origin import (
    CountLineOrigin,
)
from src.modules.inventory.domain.count_sheet.value_object.status import (
    CountSheetStatus,
)
from src.modules.inventory.domain.inventory_count.baseline_snapshot import (
    InventoryCountBaselineSnapshot,
)
from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountResultError,
    InventoryCountCoverageError,
    InventoryCountResultConflictError,
    InventoryCountResultMismatchError,
    InventoryCountSheetsNotReadyError,
    InventoryCountTimeError,
    InventoryCountVersionConflictError,
)
from src.modules.inventory.domain.inventory_count.result_snapshot import (
    InventoryCountResultSnapshot,
    InventoryCountResultLineSnapshot,
)
from src.modules.inventory.domain.inventory_count.sheet_source_snapshot import (
    InventoryCountSheetSourceSnapshot,
)
from src.modules.inventory.domain.inventory_count.time import (
    normalize_inventory_count_time,
)
from src.modules.inventory.domain.inventory_count.value_object.result_id import (
    InventoryCountResultIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.sheet_revision import (
    CountSheetRevisionVO,
)
from src.modules.inventory.domain.inventory_item.stock_snapshot import (
    InventoryItemStockSnapshot,
)
from src.modules.inventory.domain.policy.count_sheet_source import (
    CountSheetSourcePolicy,
)
from src.modules.inventory.domain.policy.count_sheet_submission import (
    CountSheetSubmissionPolicy,
)
from src.modules.inventory.domain.policy.found_count_line import FoundCountLinePolicy
from src.modules.inventory.domain.policy.inventory_count_baseline import (
    InventoryCountBaselinePolicy,
)
from src.modules.inventory.domain.stock_location.snapshot import StockLocationSnapshot
from src.modules.inventory.domain.stock_lot.snapshot import StockLotSnapshot
from src.modules.inventory.domain.stock_position.counting_snapshot import (
    StockPositionCountingSnapshot,
)
from src.modules.inventory.domain.stock_serial.snapshot import StockSerialSnapshot
from src.modules.inventory.domain.warehouse.snapshot import WarehouseSnapshot


class InventoryCountResultPolicy:
    """Собирает полное непротиворечивое покрытие основания по текущим снимкам всех ведомостей без проведения корректировок."""

    @staticmethod
    def build_result(
        *,
        identifier: InventoryCountResultIdVO,
        inventory_count: InventoryCountSheetSourceSnapshot,
        baseline: InventoryCountBaselineSnapshot,
        sheets: tuple[CountSheetReconciliationSnapshot, ...],
        prepared_at: datetime,
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        positions: tuple[StockPositionCountingSnapshot, ...],
        warehouse: WarehouseSnapshot | None = None,
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialSnapshot, ...] = (),
    ) -> InventoryCountResultSnapshot:
        """Проверяет весь переданный набор, сохраняя нулевые наблюдения и исключённые ревизии, но не выбирая источники автоматически."""
        CountSheetSourcePolicy.ensure_compatible(
            inventory_count=inventory_count, baseline=baseline
        )
        prepared = normalize_inventory_count_time(prepared_at)
        if prepared < inventory_count.updated_at:
            raise InventoryCountTimeError(
                "Подготовка результата не может предшествовать текущему состоянию родителя."
            )
        if not isinstance(sheets, tuple):
            raise InvalidInventoryCountResultError(
                "Нужен tuple полных текущих снимков всех ведомостей инвентаризации."
            )
        known = {position.id: position for position in baseline.positions}
        revisions, result_lines, observations, found = [], [], [], []
        sheet_ids, covered, dimensions = set(), set(), set()
        for sheet in sheets:
            if not isinstance(sheet, CountSheetReconciliationSnapshot):
                raise InvalidInventoryCountResultError(
                    "Нужны снимки ведомостей для сводного результата."
                )
            sheet.ensure_valid()
            if sheet.id in sheet_ids:
                raise InventoryCountResultConflictError(
                    "Снимок ведомости повторяется; нельзя выбирать последнюю версию автоматически."
                )
            sheet_ids.add(sheet.id)
            if (
                sheet.inventory_count_id != inventory_count.id
                or sheet.baseline != inventory_count.baseline
                or sheet.warehouse_id != inventory_count.warehouse_id
                or sheet.owner_id != inventory_count.owner_id
            ):
                raise InventoryCountResultMismatchError(
                    "Ведомость относится к другой инвентаризации или основанию."
                )
            if sheet.updated_at > prepared:
                raise InventoryCountTimeError(
                    "Результат не может предшествовать текущей ревизии ведомости."
                )
            if sheet.status is CountSheetStatus.DRAFT:
                raise InventoryCountSheetsNotReadyError(
                    "Перед фиксацией результата нужно передать или отменить все черновики."
                )
            revisions.append(
                CountSheetRevisionVO(
                    sheet.id, sheet.version, sheet.status, sheet.updated_at
                )
            )
            if sheet.status is not CountSheetStatus.SUBMITTED:
                continue
            for row in sheet.lines:
                line = row.as_line()
                if line.dimensions in dimensions or (
                    line.position_id is not None and line.position_id in covered
                ):
                    raise InventoryCountResultConflictError(
                        "Одна позиция или комбинация измерений посчитана в нескольких ведомостях."
                    )
                dimensions.add(line.dimensions)
                if line.origin is CountLineOrigin.BASELINE:
                    if known.get(line.position_id) != line.baseline_position_snapshot():
                        raise InventoryCountResultMismatchError(
                            "Учётные данные строки не совпадают с основанием."
                        )
                    covered.add(line.position_id)
                else:
                    found.append(line)
                observations.append(line)
                result_lines.append(
                    InventoryCountResultLineSnapshot(sheet.id, sheet.version, row)
                )
        if covered != set(known):
            raise InventoryCountCoverageError(
                "Каждая позиция основания, включая нулевую, должна быть покрыта ровно один раз."
            )
        if found:
            FoundCountLinePolicy.ensure_sources(lines=tuple(found), baseline=baseline)
        InventoryCountBaselinePolicy.ensure_unchanged(
            baseline=baseline, locations=locations, positions=positions
        )
        CountSheetSubmissionPolicy.ensure_observations(
            lines=tuple(observations),
            warehouse_id=inventory_count.warehouse_id,
            inventory_items=inventory_items,
            locations=locations,
            checked_at=prepared,
            warehouse=warehouse,
            lots=lots,
            serials=serials,
        )
        result = InventoryCountResultSnapshot(
            identifier,
            inventory_count.id,
            inventory_count.version,
            inventory_count.baseline,
            inventory_count.warehouse_id,
            inventory_count.owner_id,
            inventory_count.scope,
            prepared,
            tuple(sorted(revisions, key=lambda revision: revision.id.uuid.int)),
            tuple(
                sorted(
                    result_lines,
                    key=lambda row: (
                        row.sheet_id.uuid.int,
                        row.observation.id.uuid.int,
                    ),
                )
            ),
        )
        result.ensure_valid()
        return result

    @staticmethod
    def ensure_compatible(
        *,
        result: InventoryCountResultSnapshot,
        inventory_count: InventoryCountSheetSourceSnapshot,
        baseline: InventoryCountBaselineSnapshot,
        sheets: tuple[CountSheetReconciliationSnapshot, ...],
        inventory_items: tuple[InventoryItemStockSnapshot, ...],
        locations: tuple[StockLocationSnapshot, ...],
        positions: tuple[StockPositionCountingSnapshot, ...],
        warehouse: WarehouseSnapshot | None = None,
        lots: tuple[StockLotSnapshot, ...] = (),
        serials: tuple[StockSerialSnapshot, ...] = (),
    ) -> None:
        """Перед регистрацией заново сопоставляет результат с текущими ревизиями, наблюдениями и физическим основанием."""
        if not isinstance(result, InventoryCountResultSnapshot):
            raise InvalidInventoryCountResultError(
                "Нужен сводный результат инвентаризации."
            )
        result.ensure_valid()
        CountSheetSourcePolicy.ensure_compatible(
            inventory_count=inventory_count, baseline=baseline
        )
        if result.inventory_count_version != inventory_count.version:
            raise InventoryCountVersionConflictError(
                "Результат построен для другой версии инвентаризации."
            )
        current = InventoryCountResultPolicy.build_result(
            identifier=result.id,
            inventory_count=inventory_count,
            baseline=baseline,
            sheets=sheets,
            prepared_at=result.prepared_at,
            inventory_items=inventory_items,
            locations=locations,
            positions=positions,
            warehouse=warehouse,
            lots=lots,
            serials=serials,
        )
        if current != result:
            raise InventoryCountResultMismatchError(
                "Результат больше не соответствует полному текущему набору источников."
            )
