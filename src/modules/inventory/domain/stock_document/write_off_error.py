from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class WriteOffPostingConflictError(InventoryError):
    """Ключ списания уже связан с другим составом команды."""


class InsufficientWriteOffStockError(InventoryError):
    """Сохраняет точные количества выбранной позиции для сверки списания."""

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


class WriteOffFactNotFoundError(InventoryError):
    """Документ или факт списания отсутствует в выбранном tenant."""


class InvalidWriteOffReasonError(InventoryError):
    """Отклоняет отсутствующую, пустую или недопустимую причину списания."""
