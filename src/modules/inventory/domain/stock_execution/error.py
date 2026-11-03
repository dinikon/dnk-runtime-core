from src.modules.inventory.domain.error import InventoryError


class StockExecutionError(InventoryError):
    """Базовая ошибка фактического исполнения складского документа."""


class InvalidStockExecutionValueError(StockExecutionError):
    """Сообщает о некорректном собственном составе исполнения."""


class InvalidStockExecutionLineError(StockExecutionError):
    """Сообщает о некорректной фактической строке или её количестве."""


class InvalidStockExecutionRouteError(StockExecutionError):
    """Отклоняет неверный маршрут или подмену сохраняемых измерений."""


class InvalidStockExecutionContextError(StockExecutionError):
    """Сообщает о несовпадении реквизитов и снимков фактического контекста."""


class DuplicateStockExecutionLineError(StockExecutionError):
    """Запрещает повторные ID строк исполнения."""


class DuplicateStockExecutionSerialError(StockExecutionError):
    """Запрещает повтор одного серийного экземпляра в разных строках исполнения."""


class InvalidStockExecutionDocumentSnapshotError(StockExecutionError):
    """Сообщает о некорректном снимке исполнения для регистрации в документе."""


class StockExecutionTimeError(StockExecutionError):
    """Отклоняет время без часового пояса или нарушение хронологии исполнения."""
