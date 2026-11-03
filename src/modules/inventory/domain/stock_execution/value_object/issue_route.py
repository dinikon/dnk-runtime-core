from dataclasses import dataclass

from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionRouteError,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)


@dataclass(frozen=True, slots=True)
class IssueExecutionRouteVO:
    """Описывает расход из физических измерений без фиктивной позиции покупателя."""

    source: StockDimensionsVO

    def __post_init__(self) -> None:
        """Требует типизированный источник расхода."""
        if not isinstance(self.source, StockDimensionsVO):
            raise InvalidStockExecutionRouteError("Нужен источник StockDimensionsVO.")

    @property
    def dimensions(self) -> tuple[StockDimensionsVO, ...]:
        """Возвращает участвующие физические измерения для проверки контекста."""
        return (self.source,)
