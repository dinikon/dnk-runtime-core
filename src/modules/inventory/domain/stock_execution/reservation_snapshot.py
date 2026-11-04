from dataclasses import dataclass
from datetime import datetime, timedelta

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionReservationSnapshotError,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockExecutionReservationLineSnapshot:
    """Передаёт идентичность строки и её положительное базовое количество без маршрута и Entity."""

    id: StockExecutionLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    quantity: QuantityVO

    def ensure_valid(self) -> None:
        """Проверяет типы, известную единицу и строго положительное количество строки."""
        if (
            not isinstance(self.id, StockExecutionLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value.is_zero()
        ):
            raise InvalidStockExecutionReservationSnapshotError(
                "Нужны типизированная строка исполнения и положительное количество."
            )
        get_uom(self.base_uom)


@dataclass(frozen=True, slots=True)
class StockExecutionReservationSnapshot:
    """Передаёт фактические строки, область и время для явного сопоставления резервам."""

    id: StockExecutionIdVO
    operation_type: StockOperationType
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    executed_at: datetime
    lines: tuple[StockExecutionReservationLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет реквизиты, UTC-время и уникальные непустые фактические строки."""
        if (
            not isinstance(self.id, StockExecutionIdVO)
            or not isinstance(self.operation_type, StockOperationType)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.executed_at, datetime)
            or self.executed_at.utcoffset() != timedelta(0)
            or not isinstance(self.lines, tuple)
            or not self.lines
        ):
            raise InvalidStockExecutionReservationSnapshotError(
                "Нужен непустой снимок исполнения с типизированными реквизитами и UTC-временем."
            )
        ids = set()
        for line in self.lines:
            if not isinstance(line, StockExecutionReservationLineSnapshot):
                raise InvalidStockExecutionReservationSnapshotError(
                    "Нужны снимки строк исполнения."
                )
            line.ensure_valid()
            if line.id in ids:
                raise InvalidStockExecutionReservationSnapshotError(
                    "ID фактических строк не должны повторяться."
                )
            ids.add(line.id)
