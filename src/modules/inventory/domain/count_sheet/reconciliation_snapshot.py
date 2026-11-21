from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.count_sheet.entity.count_line import CountLine
from src.modules.inventory.domain.count_sheet.error import (
    InvalidCountSheetReconciliationSnapshotError,
)
from src.modules.inventory.domain.count_sheet.time import normalize_count_sheet_time
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
from src.modules.inventory.domain.inventory_count.value_object.baseline_ref import (
    InventoryCountBaselineRefVO,
)
from src.modules.inventory.domain.inventory_count.value_object.identifier import (
    InventoryCountIdVO,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class CountLineReconciliationSnapshot:
    """Передаёт собственные исторические значения строки без ссылки на Entity или агрегат ведомости."""

    id: CountLineIdVO
    origin: CountLineOrigin
    position_id: StockPositionIdVO | None
    dimensions: StockDimensionsVO
    base_uom: UomCodeVO
    expected_qty: QuantityVO
    position_version: int | None
    counted_qty: QuantityVO | None
    counted_at: datetime | None

    def as_line(self) -> CountLine:
        """Валидирует локальные значения прежней фабрикой неизменяемой строки без восстановления чужого корня."""
        line = CountLine.restore(
            identifier=self.id,
            origin=self.origin,
            position_id=self.position_id,
            dimensions=self.dimensions,
            base_uom=self.base_uom,
            expected_qty=self.expected_qty,
            position_version=self.position_version,
            counted_qty=self.counted_qty,
            counted_at=self.counted_at,
        )
        if self.counted_at is not None and self.counted_at.utcoffset() != timedelta(0):
            raise InvalidCountSheetReconciliationSnapshotError(
                "Снимок наблюдения должен хранить момент в UTC."
            )
        return line

    def ensure_valid(self) -> None:
        """Проверяет локальные типы, матрицу источника, парность наблюдений и SERIAL прежними правилами строки."""
        self.as_line()


@dataclass(frozen=True, slots=True)
class CountSheetReconciliationSnapshot:
    """Неизменяемое состояние одной ведомости для проверки полного набора без передачи Aggregate Root."""

    id: CountSheetIdVO
    inventory_count_id: InventoryCountIdVO
    baseline: InventoryCountBaselineRefVO
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    status: CountSheetStatus
    lines: tuple[CountLineReconciliationSnapshot, ...]
    created_at: datetime
    updated_at: datetime
    version: int

    def ensure_valid(self) -> None:
        """Проверяет собственный состав, уникальность, UTC-хронологию и заполненность переданных/отозванных ведомостей."""
        if (
            not isinstance(self.id, CountSheetIdVO)
            or not isinstance(self.inventory_count_id, InventoryCountIdVO)
            or not isinstance(self.baseline, InventoryCountBaselineRefVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.status, CountSheetStatus)
            or not isinstance(self.lines, tuple)
            or not self.lines
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidCountSheetReconciliationSnapshotError(
                "Нужен полный типизированный снимок ведомости."
            )
        self.baseline.ensure_valid()
        created = normalize_count_sheet_time(self.created_at)
        updated = normalize_count_sheet_time(self.updated_at)
        if (
            self.created_at.utcoffset() != timedelta(0)
            or self.updated_at.utcoffset() != timedelta(0)
            or not self.baseline.snapshot_at <= created <= updated
        ):
            raise InvalidCountSheetReconciliationSnapshotError(
                "Хронология ведомости должна быть в UTC и не предшествовать основанию."
            )
        ids, positions, dimensions = set(), set(), set()
        for row in self.lines:
            if not isinstance(row, CountLineReconciliationSnapshot):
                raise InvalidCountSheetReconciliationSnapshotError(
                    "Нужны снимки строк ведомости."
                )
            line = row.as_line()
            if (
                line.id in ids
                or line.dimensions in dimensions
                or (line.position_id is not None and line.position_id in positions)
            ):
                raise InvalidCountSheetReconciliationSnapshotError(
                    "Строки, позиции и измерения снимка повторяются."
                )
            ids.add(line.id)
            dimensions.add(line.dimensions)
            if line.position_id is not None:
                positions.add(line.position_id)
            if line.dimensions.owner_id != self.owner_id:
                raise InvalidCountSheetReconciliationSnapshotError(
                    "Владелец строки не соответствует ведомости."
                )
            if (
                line.counted_at is not None
                and not created <= line.counted_at <= updated
            ):
                raise InvalidCountSheetReconciliationSnapshotError(
                    "Момент наблюдения вне хронологии ведомости."
                )
            if (
                self.status in (CountSheetStatus.SUBMITTED, CountSheetStatus.WITHDRAWN)
                and line.counted_qty is None
            ):
                raise InvalidCountSheetReconciliationSnapshotError(
                    "Переданная или отозванная ведомость должна быть посчитана."
                )
