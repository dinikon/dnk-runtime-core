from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionTransferSnapshotError,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
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
class StockExecutionTransferLineSnapshot:
    """Передаёт целую строку расхода или прихода с единственным набором физических измерений."""

    id: StockExecutionLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    quantity: QuantityVO
    dimensions: StockDimensionsVO

    def ensure_valid(self) -> None:
        """Проверяет положительность, согласованность товара и единичность конкретного серийного экземпляра."""
        if (
            not isinstance(self.id, StockExecutionLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value.is_zero()
            or not isinstance(self.dimensions, StockDimensionsVO)
            or self.dimensions.inventory_item_id != self.inventory_item_id
        ):
            raise InvalidStockExecutionTransferSnapshotError(
                "Нужна типизированная фактическая строка с положительным количеством и измерениями того же товара."
            )
        get_uom(self.base_uom)
        if self.dimensions.serial_id is not None and (
            self.base_uom != UomCodeVO("PCS") or self.quantity.value != Decimal(1)
        ):
            raise InvalidStockExecutionTransferSnapshotError(
                "Конкретный серийный экземпляр требует 1 PCS."
            )


@dataclass(frozen=True, slots=True)
class StockExecutionTransferSnapshot:
    """Передаёт расход или приход для согласования отправки с сохранением LOT/SERIAL и состояния."""

    id: StockExecutionIdVO
    operation_type: StockOperationType
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO
    executed_at: datetime
    lines: tuple[StockExecutionTransferLineSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет ISSUE/RECEIPT, UTC, уникальность фактических строк/серий и владельца измерений."""
        if (
            not isinstance(self.id, StockExecutionIdVO)
            or not isinstance(self.operation_type, StockOperationType)
            or self.operation_type
            not in (StockOperationType.ISSUE, StockOperationType.RECEIPT)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or not isinstance(self.executed_at, datetime)
            or self.executed_at.utcoffset() != timedelta(0)
            or not isinstance(self.lines, tuple)
            or not self.lines
        ):
            raise InvalidStockExecutionTransferSnapshotError(
                "Нужен непустой снимок ISSUE/RECEIPT с UTC-временем и типизированными ссылками."
            )
        ids, serials = set(), set()
        for line in self.lines:
            if not isinstance(line, StockExecutionTransferLineSnapshot):
                raise InvalidStockExecutionTransferSnapshotError(
                    "Нужны снимки фактических строк перемещения."
                )
            line.ensure_valid()
            serial = line.dimensions.serial_id
            if (
                line.id in ids
                or line.dimensions.owner_id != self.owner_id
                or (serial is not None and serial in serials)
            ):
                raise InvalidStockExecutionTransferSnapshotError(
                    "Строки и серийные экземпляры уникальны, владелец измерений должен совпадать с исполнением."
                )
            ids.add(line.id)
            if serial is not None:
                serials.add(serial)
