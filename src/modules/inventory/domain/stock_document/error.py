from src.modules.inventory.domain.error import InventoryError


class StockDocumentError(InventoryError):
    """Базовая ошибка планового складского документа."""


class InvalidStockDocumentValueError(StockDocumentError):
    """Сообщает о некорректном собственном составе документа."""


class InvalidStockDocumentLineError(StockDocumentError):
    """Сообщает о неверных типах или неположительном количестве строки."""


class InvalidDocumentSourceError(StockDocumentError):
    """Сообщает о некорректной внешней ссылке основания документа."""


class StockDocumentNotDraftError(StockDocumentError):
    """Запрещает редактировать, подтверждать или отменять завершённый план."""


class EmptyStockDocumentError(StockDocumentError):
    """Запрещает подтверждение пустого плана."""


class StockDocumentLineConflictError(StockDocumentError):
    """Сообщает о повторном идентификаторе плановой строки."""


class StockDocumentLineNotFoundError(StockDocumentError):
    """Сообщает об отсутствии строки в данном документе."""


class InvalidStockDocumentContextError(StockDocumentError):
    """Сообщает о несовпадении склада или набора снимков товаров с документом."""


class StockDocumentItemMismatchError(StockDocumentError):
    """Запрещает проверять строку по снимку другого товара."""


class StockDocumentUomMismatchError(StockDocumentError):
    """Запрещает переинтерпретировать количество строки в новой базовой единице."""


class StockDocumentTimeError(InvalidStockDocumentValueError):
    """Сообщает о некорректном времени или нарушении хронологии документа."""


class InvalidStockDocumentExecutionSnapshotError(StockDocumentError):
    """Сообщает о некорректном снимке плана и накопленного исполнения."""


class StockDocumentExecutionNotAllowedError(StockDocumentError):
    """Запрещает регистрировать исполнение в неподходящем состоянии документа."""


class StaleStockDocumentVersionError(StockDocumentError):
    """Отклоняет исполнение, подготовленное по другой версии плана."""


class StockDocumentOverExecutionError(StockDocumentError):
    """Запрещает суммарное выполнение сверх планового количества строки."""
