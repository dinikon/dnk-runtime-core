from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from src.modules.inventory.domain.policy.stock_posting import StockPostingPolicy
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_posting.error import (
    InvalidStockMovementValuationSnapshotError,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.movement_entry_pair import (
    StockMovementEntryPairVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class StockMovementValuationSnapshot:
    """Фиксирует проверяемое основание пары INTERNAL_MOVE без цены, потребления или создания стоимостных слоёв."""

    posting_id: StockPostingIdVO
    pair: StockMovementEntryPairVO
    source_position: StockPositionSnapshot
    target_position: StockPositionSnapshot
    warehouse_id: WarehouseIdVO
    quantity: QuantityVO
    moved_at: datetime

    def ensure_valid(self) -> None:
        """Проверяет типы, сохраняемые измерения, разные адреса, положительное количество, SERIAL и UTC-время."""
        if (
            not isinstance(self.posting_id, StockPostingIdVO)
            or not isinstance(self.pair, StockMovementEntryPairVO)
            or not isinstance(self.source_position, StockPositionSnapshot)
            or not isinstance(self.target_position, StockPositionSnapshot)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.quantity, QuantityVO)
            or not isinstance(self.quantity.value, Decimal)
            or not self.quantity.value.is_finite()
            or self.quantity.value <= 0
        ):
            raise InvalidStockMovementValuationSnapshotError(
                "Нужны номинальные поля пары перемещения и положительный конечный QuantityVO."
            )
        self.pair.ensure_valid()
        self.source_position.ensure_valid()
        self.target_position.ensure_valid()
        source = self.source_position.dimensions
        target = self.target_position.dimensions
        if (
            self.source_position.id == self.target_position.id
            or source.location_id == target.location_id
            or self.source_position.base_uom != self.target_position.base_uom
            or (
                source.inventory_item_id,
                source.owner_id,
                source.lot_id,
                source.serial_id,
                source.stock_status,
            )
            != (
                target.inventory_item_id,
                target.owner_id,
                target.lot_id,
                target.serial_id,
                target.stock_status,
            )
        ):
            raise InvalidStockMovementValuationSnapshotError(
                "Разные позиции и локации должны сохранять товар, владельца, LOT/SERIAL, состояние и единицу."
            )
        if source.serial_id is not None and (
            self.source_position.base_uom != UomCodeVO("PCS")
            or self.quantity.value != 1
        ):
            raise InvalidStockMovementValuationSnapshotError(
                "Перемещение конкретной серии требует ровно одну PCS."
            )
        StockPostingPolicy.normalize_time(self.moved_at)
        if self.moved_at.utcoffset() != timedelta(0):
            raise InvalidStockMovementValuationSnapshotError(
                "Готовое основание перемещения хранит время в UTC."
            )
