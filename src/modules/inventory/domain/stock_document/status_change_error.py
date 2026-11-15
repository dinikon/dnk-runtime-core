from src.modules.inventory.domain.error import InventoryError
from src.modules.inventory.domain.stock_position.value_object.identifier import (
    StockPositionIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


class StatusChangePostingConflictError(InventoryError):
    """Ключ изменения состояния уже связан с другим составом команды."""


class InsufficientStatusChangeStockError(InventoryError):
    """Сохраняет точные количества выбранной позиции для сверки изменения состояния."""

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


class StatusChangeFactNotFoundError(InventoryError):
    """Документ или факт изменения состояния отсутствует в выбранном tenant."""


class InvalidStatusChangeReasonError(InventoryError):
    """Отклоняет отсутствующую, пустую или недопустимую причину изменения состояния."""


class InvalidStockStatusChangeError(InventoryError):
    """Запрещает переход в прежнее состояние или несогласованное основание операции."""


class StockStatusChangeBalanceError(InventoryError):
    """Отклоняет несохранённое количество или замену сохраняемых измерений."""
