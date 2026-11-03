from src.modules.inventory.domain.error import InventoryError


class StockPostingError(InventoryError):
    """Базовая ошибка проведения физического движения."""


class InvalidStockPostingValueError(StockPostingError):
    """Сообщает о некорректном собственном составе проведения или времени."""


class InvalidPostingSourceError(StockPostingError):
    """Сообщает о некорректной ссылке на исполнение."""


class InvalidStockLedgerEntryError(StockPostingError):
    """Сообщает о некорректном собственном составе записи журнала."""


class ZeroStockLedgerDeltaError(StockPostingError):
    """Запрещает нулевую запись физического движения."""


class DuplicateStockLedgerEntryError(StockPostingError):
    """Запрещает повторные идентификаторы записей и позиций внутри проведения."""


class StockPostingSignError(StockPostingError):
    """Сообщает о несовместимости знака записей с видом обычной операции."""


class InvalidPostingContextError(StockPostingError):
    """Сообщает об отсутствующих, лишних или несовместимых снимках позиций и локаций."""


class StockMovementBalanceError(StockPostingError):
    """Запрещает изменение количества или сохраняемых измерений внутренним перемещением."""


class InvalidStockReversalError(StockPostingError):
    """Сообщает о некорректном основании, времени или идентичности компенсации."""


class InvalidStockPostingSnapshotError(StockPostingError):
    """Сообщает о некорректном снимке исходного проведения."""
