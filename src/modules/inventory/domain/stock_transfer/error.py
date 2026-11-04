from src.modules.inventory.domain.error import InventoryError


class StockTransferError(InventoryError):
    """Базовая ошибка плана межскладского перемещения."""


class InvalidStockTransferValueError(StockTransferError):
    """Сообщает о некорректном собственном составе или версии перемещения."""


class InvalidStockTransferLineError(StockTransferError):
    """Сообщает о неверных типах или неположительном плане строки перемещения."""


class InvalidStockTransferContextError(StockTransferError):
    """Сообщает о несовпадении складов или составе переданных товарных снимков."""


class StockTransferSameWarehouseError(StockTransferError):
    """Запрещает планировать межскладское перемещение внутри одного склада."""


class StockTransferStatusError(StockTransferError):
    """Запрещает редактирование, подтверждение и отмену вне черновика перемещения."""


class StockTransferVersionConflictError(StockTransferError):
    """Отклоняет изменение по устаревшей версии плана перемещения."""


class StockTransferTimeError(InvalidStockTransferValueError):
    """Требует явное aware-время, UTC-хранение и неубывающую хронологию."""


class StockTransferLineConflictError(StockTransferError):
    """Запрещает повтор идентификатора строки внутри одного перемещения."""


class StockTransferLineNotFoundError(StockTransferError):
    """Сообщает об отсутствии строки в данном плане перемещения."""


class StockTransferItemMismatchError(StockTransferError):
    """Запрещает проверять или менять строку по снимку другого товара."""


class StockTransferUomMismatchError(StockTransferError):
    """Запрещает переинтерпретировать строку в другой базовой единице товара."""


class EmptyStockTransferError(StockTransferError):
    """Запрещает подтверждённый план перемещения без строк."""
