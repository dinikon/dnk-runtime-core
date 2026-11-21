from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO
from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO


class InvalidStockReturnError(InventoryError):
    """Основание, направление или идентичность возврата недопустимы."""


class StockReturnLimitError(InventoryError):
    """Возврат превышает ещё не возвращённую часть исходной фактической строки."""

    def __init__(
        self,
        message: str,
        *,
        origin_line_id: StockExecutionLineIdVO,
        requested: QuantityVO,
        remaining: QuantityVO,
    ) -> None:
        """Сохраняет точные значения для отображения конфликта основания."""
        super().__init__(message)
        self.origin_line_id, self.requested, self.remaining = (
            origin_line_id,
            requested,
            remaining,
        )


class ReturnPostingConflictError(InventoryError):
    """Ключ возврата уже связан с другим составом команды."""


class InsufficientReturnStockError(InventoryError):
    """Сохраняет точные количества выбранной позиции для сверки возврата."""

    def __init__(
        self,
        message: str,
        *,
        position_id: StockPositionIdVO,
        requested: QuantityVO,
        current: QuantityVO,
        base_uom: UomCodeVO,
    ) -> None:
        """Передаёт доменные значения без HTTP или ORM-зависимостей."""
        super().__init__(message)
        self.position_id = position_id
        self.requested = requested
        self.current = current
        self.base_uom = base_uom


class ReturnFactNotFoundError(InventoryError):
    """Документ или факт возврата отсутствует в выбранном tenant."""


class InvalidReturnReasonError(InventoryError):
    """Отклоняет отсутствующую, пустую или недопустимую причину возврата."""
