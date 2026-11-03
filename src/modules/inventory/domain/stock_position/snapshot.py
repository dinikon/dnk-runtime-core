from dataclasses import dataclass

from src.modules.inventory.domain.stock_position.error import (
    InvalidStockPositionSnapshotError,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class StockPositionSnapshot:
    """Фиксирует только идентичность, измерения и базовую единицу позиции для журнала."""

    id: StockPositionIdVO
    dimensions: StockDimensionsVO
    base_uom: UomCodeVO

    def ensure_valid(self) -> None:
        """Проверяет типы, известную единицу и поштучность серий без текущего остатка."""
        if (
            not isinstance(self.id, StockPositionIdVO)
            or not isinstance(self.dimensions, StockDimensionsVO)
            or not isinstance(self.base_uom, UomCodeVO)
        ):
            raise InvalidStockPositionSnapshotError(
                "Нужен типизированный снимок позиции."
            )
        get_uom(self.base_uom)
        if self.dimensions.serial_id is not None and self.base_uom != UomCodeVO("PCS"):
            raise InvalidStockPositionSnapshotError("Серийная позиция требует PCS.")
