from dataclasses import dataclass, replace
from typing import Self
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.value_object.stock_status import StockStatus
from src.modules.inventory.domain.policy.stock_status_transition import (
    StockStatusTransitionPolicy,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionRouteError,
)


@dataclass(frozen=True, slots=True)
class StatusChangeExecutionRouteVO:
    """Описывает одно количество между состояниями с неизменной физической идентичностью."""

    source: StockDimensionsVO
    destination: StockDimensionsVO

    def __post_init__(self) -> None:
        """Разрешает изменить только состояние и проверяет направленный переход."""
        if (
            not isinstance(self.source, StockDimensionsVO)
            or not isinstance(self.destination, StockDimensionsVO)
            or replace(self.source, stock_status=self.destination.stock_status)
            != self.destination
        ):
            raise InvalidStockExecutionRouteError(
                "Изменение состояния сохраняет все остальные измерения."
            )
        StockStatusTransitionPolicy.ensure_allowed(
            self.source.stock_status, self.destination.stock_status
        )

    @classmethod
    def to_status(cls, source: StockDimensionsVO, target_status: StockStatus) -> Self:
        """Выводит назначение из источника без возможности заменить остальные измерения."""
        if not isinstance(source, StockDimensionsVO):
            raise InvalidStockExecutionRouteError(
                "Нужны типизированные измерения источника."
            )
        return cls(source, replace(source, stock_status=target_status))

    @property
    def dimensions(self) -> tuple[StockDimensionsVO, ...]:
        """Возвращает обе позиции одного физического изменения состояния."""
        return (self.source, self.destination)
