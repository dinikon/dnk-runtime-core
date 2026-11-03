from dataclasses import dataclass, replace

from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionRouteError,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)


@dataclass(frozen=True, slots=True)
class InternalMoveExecutionRouteVO:
    """Описывает одно количество между разными адресами с сохранением остальных измерений."""

    source: StockDimensionsVO
    destination: StockDimensionsVO

    def __post_init__(self) -> None:
        """Запрещает одинаковые адреса и замену товара, владельца, партии, серии или состояния."""
        if (
            not isinstance(self.source, StockDimensionsVO)
            or not isinstance(self.destination, StockDimensionsVO)
            or self.source.location_id == self.destination.location_id
            or replace(self.source, location_id=self.destination.location_id)
            != self.destination
        ):
            raise InvalidStockExecutionRouteError(
                "Перемещение меняет только локацию и требует разные адреса."
            )

    @property
    def dimensions(self) -> tuple[StockDimensionsVO, ...]:
        """Возвращает обе стороны единственного физического перемещения."""
        return (self.source, self.destination)
