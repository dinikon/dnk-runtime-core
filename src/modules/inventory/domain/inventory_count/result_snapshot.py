from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.count_sheet.reconciliation_snapshot import (
    CountLineReconciliationSnapshot,
)
from src.modules.inventory.domain.count_sheet.value_object.identifier import (
    CountSheetIdVO,
)
from src.modules.inventory.domain.count_sheet.value_object.status import (
    CountSheetStatus,
)
from src.modules.inventory.domain.inventory_count.error import (
    InvalidInventoryCountResultError,
    InventoryCountResultConflictError,
    InventoryCountSerialConflictError,
)
from src.modules.inventory.domain.inventory_count.time import (
    normalize_inventory_count_time,
)
from src.modules.inventory.domain.inventory_count.value_object.baseline_ref import (
    InventoryCountBaselineRefVO,
)
from src.modules.inventory.domain.inventory_count.value_object.identifier import (
    InventoryCountIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.result_id import (
    InventoryCountResultIdVO,
)
from src.modules.inventory.domain.inventory_count.value_object.scope import CountScopeVO
from src.modules.inventory.domain.inventory_count.value_object.sheet_revision import (
    CountSheetRevisionVO,
)
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class InventoryCountResultLineSnapshot:
    """Сохраняет наблюдение вместе с точной исходной ведомостью и её версией."""

    sheet_id: CountSheetIdVO
    sheet_version: int
    observation: CountLineReconciliationSnapshot

    def ensure_valid(self) -> None:
        """Требует типизированное происхождение и заполненное, локально корректное наблюдение."""
        if (
            not isinstance(self.sheet_id, CountSheetIdVO)
            or type(self.sheet_version) is not int
            or self.sheet_version < 0
            or not isinstance(self.observation, CountLineReconciliationSnapshot)
        ):
            raise InvalidInventoryCountResultError(
                "Нужны происхождение и снимок строки результата."
            )
        self.observation.ensure_valid()
        if self.observation.counted_qty is None:
            raise InvalidInventoryCountResultError(
                "Строка результата должна быть посчитана."
            )

    @property
    def discrepancy(self) -> StockDeltaVO:
        """Вычисляет точную дельту прежним правилом строки без хранения производного значения."""
        self.ensure_valid()
        delta = self.observation.as_line().discrepancy
        if delta is None:
            raise InvalidInventoryCountResultError(
                "Нельзя получить расхождение непосчитанной строки."
            )
        return delta


@dataclass(frozen=True, slots=True)
class InventoryCountResultSnapshot:
    """Неизменяемый сводный результат с полным составом ревизий и наблюдениями вне корня инвентаризации."""

    id: InventoryCountResultIdVO
    inventory_count_id: InventoryCountIdVO
    inventory_count_version: int
    baseline: InventoryCountBaselineRefVO
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    scope: CountScopeVO
    prepared_at: datetime
    sheet_revisions: tuple[CountSheetRevisionVO, ...]
    lines: tuple[InventoryCountResultLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет собственную структуру, происхождение, уникальность и фактическую согласованность SERIAL в области."""
        if (
            not isinstance(self.id, InventoryCountResultIdVO)
            or not isinstance(self.inventory_count_id, InventoryCountIdVO)
            or type(self.inventory_count_version) is not int
            or self.inventory_count_version < 0
            or not isinstance(self.baseline, InventoryCountBaselineRefVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.scope, CountScopeVO)
            or not isinstance(self.sheet_revisions, tuple)
            or not isinstance(self.lines, tuple)
        ):
            raise InvalidInventoryCountResultError(
                "Нужен полный типизированный состав сводного результата."
            )
        self.baseline.ensure_valid()
        self.scope.ensure_valid()
        prepared = normalize_inventory_count_time(self.prepared_at)
        if (
            self.prepared_at.utcoffset() != timedelta(0)
            or prepared < self.baseline.snapshot_at
        ):
            raise InvalidInventoryCountResultError(
                "Результат требует UTC-момент не раньше основания."
            )
        revisions = {}
        for revision in self.sheet_revisions:
            if not isinstance(revision, CountSheetRevisionVO):
                raise InvalidInventoryCountResultError(
                    "Нужны ревизии всех исходных ведомостей."
                )
            revision.ensure_valid()
            if revision.id in revisions:
                raise InventoryCountResultConflictError(
                    "Ведомость повторяется в составе результата."
                )
            if (
                revision.status is CountSheetStatus.DRAFT
                or revision.updated_at > prepared
            ):
                raise InvalidInventoryCountResultError(
                    "Ревизия не готова или находится позже подготовки результата."
                )
            revisions[revision.id] = revision
        sources, positions, dimensions, used = set(), set(), set(), set()
        serial_identity, serial_positive = {}, set()
        for row in self.lines:
            if not isinstance(row, InventoryCountResultLineSnapshot):
                raise InvalidInventoryCountResultError("Нужны снимки строк результата.")
            row.ensure_valid()
            line = row.observation
            revision = revisions.get(row.sheet_id)
            if (
                revision is None
                or revision.status is not CountSheetStatus.SUBMITTED
                or revision.version != row.sheet_version
                or line.counted_at > revision.updated_at
                or line.counted_at < self.baseline.snapshot_at
                or line.dimensions.owner_id != self.owner_id
            ):
                raise InvalidInventoryCountResultError(
                    "Наблюдение не соответствует переданной исходной ведомости и области."
                )
            key = (row.sheet_id, line.id)
            if (
                key in sources
                or line.dimensions in dimensions
                or (line.position_id is not None and line.position_id in positions)
            ):
                raise InventoryCountResultConflictError(
                    "Источники, позиции или измерения результата повторяются."
                )
            sources.add(key)
            dimensions.add(line.dimensions)
            used.add(row.sheet_id)
            if line.position_id is not None:
                positions.add(line.position_id)
            serial_id = line.dimensions.serial_id
            if serial_id is not None:
                identity = (
                    line.dimensions.inventory_item_id,
                    line.dimensions.lot_id,
                    line.base_uom,
                )
                previous = serial_identity.get(serial_id)
                if previous is not None and previous != identity:
                    raise InventoryCountSerialConflictError(
                        "Один SERIAL не может обозначать разные товары, партии или единицы."
                    )
                serial_identity[serial_id] = identity
                if not line.counted_qty.value.is_zero():
                    if serial_id in serial_positive:
                        raise InventoryCountSerialConflictError(
                            "SERIAL положительно посчитан более чем в одной позиции области."
                        )
                    serial_positive.add(serial_id)
        if used != {
            revision.id
            for revision in self.sheet_revisions
            if revision.status is CountSheetStatus.SUBMITTED
        }:
            raise InvalidInventoryCountResultError(
                "Каждая переданная ведомость должна иметь строки в результате."
            )
