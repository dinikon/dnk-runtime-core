from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.stock_position.error import (
    InvalidSerialStockQuantityError,
    InvalidStockPositionAvailabilitySnapshotError,
)
from src.modules.inventory.domain.stock_position.snapshot import StockPositionSnapshot
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class StockPositionAvailabilitySnapshot:
    """Передаёт идентичность, измерения, единицу и физическое количество без истории и резервов."""

    id: StockPositionIdVO
    dimensions: StockDimensionsVO
    base_uom: UomCodeVO
    on_hand_qty: QuantityVO

    def ensure_valid(self) -> None:
        """Проверяет собственные типы и ограничение конкретного экземпляра нулём или единицей."""
        if (
            not isinstance(self.id, StockPositionIdVO)
            or not isinstance(self.dimensions, StockDimensionsVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.on_hand_qty, QuantityVO)
        ):
            raise InvalidStockPositionAvailabilitySnapshotError(
                "Нужен типизированный снимок физического количества позиции."
            )
        StockPositionSnapshot(self.id, self.dimensions, self.base_uom).ensure_valid()
        if self.dimensions.serial_id is not None and self.on_hand_qty.value not in (
            Decimal(0),
            Decimal(1),
        ):
            raise InvalidSerialStockQuantityError(
                "Конкретная серия требует остаток 0 или 1 PCS."
            )
