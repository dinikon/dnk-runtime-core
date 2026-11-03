from dataclasses import dataclass

from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionRouteError,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)


@dataclass(frozen=True, slots=True)
class ReceiptExecutionRouteVO:
    """Описывает приход в конкретные физические измерения без фиктивного внешнего остатка."""

    destination: StockDimensionsVO

    def __post_init__(self) -> None:
        """Требует типизированное назначение прихода."""
        if not isinstance(self.destination, StockDimensionsVO):
            raise InvalidStockExecutionRouteError("Нужно назначение StockDimensionsVO.")

    @property
    def dimensions(self) -> tuple[StockDimensionsVO, ...]:
        """Возвращает участвующие физические измерения для проверки контекста."""
        return (self.destination,)
