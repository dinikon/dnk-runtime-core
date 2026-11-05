from dataclasses import dataclass

from src.modules.inventory.domain.stock_position.availability_snapshot import (
    StockPositionAvailabilitySnapshot,
)
from src.modules.inventory.domain.stock_position.error import (
    InvalidStockPositionCountingSnapshotError,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class StockPositionCountingSnapshot:
    """Фиксирует физическое количество и версию позиции без вычитания резервов и истории."""

    id: StockPositionIdVO
    dimensions: StockDimensionsVO
    base_uom: UomCodeVO
    on_hand_qty: QuantityVO
    version: int

    def ensure_valid(self) -> None:
        """Проверяет типы, версию, известную единицу и поштучность конкретного SERIAL."""
        if (
            not isinstance(self.id, StockPositionIdVO)
            or not isinstance(self.dimensions, StockDimensionsVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.on_hand_qty, QuantityVO)
            or type(self.version) is not int
            or self.version < 0
        ):
            raise InvalidStockPositionCountingSnapshotError(
                "Нужны типизированные количество и версия позиции."
            )
        StockPositionAvailabilitySnapshot(
            self.id, self.dimensions, self.base_uom, self.on_hand_qty
        ).ensure_valid()
