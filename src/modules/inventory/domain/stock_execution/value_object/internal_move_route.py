from dataclasses import dataclass, replace
from typing import Self
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)

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

    @classmethod
    def to_location(
        cls, source: StockDimensionsVO, destination_location_id: StockLocationIdVO
    ) -> Self:
        """Выводит назначение из источника, позволяя изменить только адрес."""
        if not isinstance(source, StockDimensionsVO) or not isinstance(
            destination_location_id, StockLocationIdVO
        ):
            raise InvalidStockExecutionRouteError(
                "Нужны измерения источника и типизированный адрес назначения."
            )
        return cls(source, replace(source, location_id=destination_location_id))

    @property
    def dimensions(self) -> tuple[StockDimensionsVO, ...]:
        """Возвращает обе стороны единственного физического перемещения."""
        return (self.source, self.destination)
