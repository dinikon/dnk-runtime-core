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
    """Отклоняет операцию вне допустимого состояния жизненного цикла перемещения."""


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


class InvalidStockTransferTransitError(StockTransferError):
    """Сообщает о некорректных ссылках транзитного маршрута."""


class InvalidStockTransferExecutionBindingError(StockTransferError):
    """Требует типизированное назначение фактической строки строке перемещения."""


class InvalidStockTransferDispatchPlanSnapshotError(StockTransferError):
    """Сообщает о некорректном снимке текущего плана и отправленного количества."""


class InvalidStockTransferDispatchSnapshotError(StockTransferError):
    """Сообщает о некорректном результате согласованной отправки в транзит."""


class StockTransferTransitMismatchError(StockTransferError):
    """Отклоняет неподходящий транзит или замену уже зафиксированного маршрута."""


class StockTransferDispatchMismatchError(StockTransferError):
    """Отклоняет несовместимые факты, область или назначения отправки."""


class UnbalancedStockTransferDispatchError(StockTransferDispatchMismatchError):
    """Запрещает различие количеств или сохраняемых измерений расхода и прихода в транзит."""


class StockTransferDispatchQuantityExceededError(StockTransferError):
    """Запрещает накопленную отправку сверх планового количества строки."""


class StockTransferReceiptQuantityExceededError(StockTransferError):
    """Запрещает приёмку сверх отправленного количества строки."""


class InvalidStockTransferReceiptPlanSnapshotError(StockTransferError):
    """Сообщает о неверном снимке плана и прогресса приёмки."""


class InvalidStockTransferReceiptSnapshotError(StockTransferError):
    """Сообщает о некорректном результате согласованной приёмки."""


class StockTransferReceiptMismatchError(StockTransferError):
    """Отклоняет несовместимые факты, область или назначения приёмки."""


class UnbalancedStockTransferReceiptError(StockTransferReceiptMismatchError):
    """Запрещает изменение количества или состава между расходом транзита и приходом на конечный склад."""


class InvalidStockTransferTransitBalanceError(StockTransferError):
    """Отклоняет неверный снимок остатка или неполную/несогласованную историю транзита."""


class StockTransferTransitStockExceededError(StockTransferError):
    """Запрещает приёмку сверх транзитного остатка конкретной строки, партии, серии и состояния."""


class InvalidStockTransferDispatchDocumentSnapshotError(StockTransferError):
    """Сообщает о неверном снимке открытого плана для документов отправки."""
