from src.modules.inventory.domain.error import InventoryError


class StockDocumentError(InventoryError):
    """Базовая ошибка планового складского документа."""


class InvalidStockAdjustmentLineError(StockDocumentError):
    """Отклоняет неверные измерения, основание или нулевую дельту корректировки."""


class InventoryCountAdjustmentMismatchError(StockDocumentError):
    """Отклоняет несоответствие документа зарегистрированному результату инвентаризации."""


class StockAdjustmentDocumentImmutableError(StockDocumentError):
    """Запрещает ручное редактирование строк документа, производного от результата пересчёта."""


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


class InvalidDocumentLineSourceError(StockDocumentError):
    """Сообщает о некорректной универсальной ссылке основания строки документа."""


class InvalidShipmentDocumentLineBindingError(StockDocumentError):
    """Требует типизированное однократное назначение новых ID строк документа строкам отправления."""


class StockDocumentShipmentMismatchError(StockDocumentError):
    """Отклоняет несовместимые основание отправления, область и состав его расходного документа."""


class StaleShipmentDocumentSourceError(StockDocumentError):
    """Отклоняет подтверждение документа по изменившейся версии отправления."""


class StockDocumentShipmentQuantityExceededError(StockDocumentError):
    """Запрещает планировать по строке отправления больше её текущего остатка."""


class InvalidStockDocumentShipmentSnapshotError(StockDocumentError):
    """Сообщает о некорректном снимке происхождения и прогресса расходного документа Shipment."""


class InvalidStockTransferDispatchDocumentLineBindingError(StockDocumentError):
    """Требует однократное назначение новых ID строк обеих сторон строкам перемещения."""


class InvalidStockDocumentTransferDispatchSnapshotError(StockDocumentError):
    """Сообщает о неверном снимке плана документа отправки перемещения."""


class StockDocumentTransferDispatchMismatchError(StockDocumentError):
    """Отклоняет несовместимые основания, роли, склады или строки документов отправки."""


class StaleStockTransferDocumentSourceError(StockDocumentError):
    """Отклоняет подтверждение по изменившейся версии основания перемещения."""


class StockDocumentTransferDispatchQuantityExceededError(StockDocumentError):
    """Запрещает план документа сверх текущего остатка к отправке."""


class UnbalancedStockTransferDispatchDocumentsError(
    StockDocumentTransferDispatchMismatchError
):
    """Запрещает различие плановых строк и количеств расхода A и прихода T."""


class InvalidStockTransferReceiptDocumentLineBindingError(StockDocumentError):
    """Требует уникальные новые ID обеих сторон приёмки для всех открытых строк транзита."""


class InvalidStockDocumentTransferReceiptSnapshotError(StockDocumentError):
    """Сообщает о некорректном снимке документа приёмки StockTransfer."""


class StockDocumentTransferReceiptMismatchError(StockDocumentError):
    """Отклоняет несовместимые основания, роли, склады или строки документов приёмки."""


class StockDocumentTransferReceiptQuantityExceededError(StockDocumentError):
    """Запрещает план приёмки сверх отправленного, но ещё не принятого количества."""


class UnbalancedStockTransferReceiptDocumentsError(
    StockDocumentTransferReceiptMismatchError
):
    """Запрещает разные планы расхода T и прихода B по строкам перемещения."""
