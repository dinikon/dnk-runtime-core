from dataclasses import dataclass
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_position.value_object.dimensions import (
    StockDimensionsVO,
)
from src.modules.inventory.domain.stock_document.return_error import (
    InvalidStockReturnError,
)


@dataclass(frozen=True, slots=True)
class ReturnReceiptExecutionRouteVO:
    """Связывает физическую сторону возврата с исходной фактической строкой."""

    origin_line_id: StockExecutionLineIdVO
    destination: StockDimensionsVO

    def __post_init__(self) -> None:
        """Проверяет полную типизированную идентичность маршрута."""
        if not isinstance(
            self.origin_line_id, StockExecutionLineIdVO
        ) or not isinstance(self.destination, StockDimensionsVO):
            raise InvalidStockReturnError("Нужны исходная строка и измерения возврата.")

    @property
    def dimensions(self) -> tuple[StockDimensionsVO, ...]:
        """Возвращает единственную физическую позицию этой стороны возврата."""
        return (self.destination,)
