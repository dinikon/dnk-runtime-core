from src.modules.inventory.domain.error import InventoryError


class StockPostingError(InventoryError):
    """Базовая ошибка проведения физического движения."""


class InvalidStockMovementEntryPairError(StockPostingError):
    """Требует различные номинальные ссылки на расходную и приходную записи перемещения."""


class StockMovementValuationSourceError(StockPostingError):
    """Отклоняет неподходящее проведение или несогласованную пару записей внутреннего перемещения."""


class InvalidStockMovementValuationSnapshotError(StockPostingError):
    """Отклоняет некорректное основание будущего переноса стоимости между позициями."""


class InvalidStockPostingFifoPlanError(StockPostingError):
    """Отклоняет неполное или несогласованное FIFO-основание всего расходного проведения."""


class StockReceiptValuationSourceError(StockPostingError):
    """Отклоняет неподходящий приход или несовпадающий контекст записи для фиксации стоимости."""


class InvalidStockReceiptValuationSnapshotError(StockPostingError):
    """Требует типизированное положительное основание стоимости с историческим временем UTC."""


class StockIssueValuationSourceError(StockPostingError):
    """Отклоняет неподходящий расход или несовпадающий контекст записи для потребления стоимости."""


class InvalidStockIssueValuationSnapshotError(StockPostingError):
    """Требует типизированное основание расхода с положительным модулем количества и UTC-временем."""


class InvalidStockPostingValueError(StockPostingError):
    """Сообщает о некорректном собственном составе проведения или времени."""


class InvalidPostingSourceError(StockPostingError):
    """Сообщает о некорректной ссылке на исполнение."""


class InvalidStockLedgerEntryError(StockPostingError):
    """Сообщает о некорректном собственном составе записи журнала."""


class InvalidStockLedgerEntrySnapshotError(InvalidStockLedgerEntryError):
    """Сообщает о некорректном снимке записи для применения к физической позиции."""


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


class InvalidStockPostingEntryBindingError(InvalidPostingContextError):
    """Сообщает о некорректном соответствии позиции и идентификатора записи Ledger."""


class OpposingStockPositionMovementsError(StockPostingError):
    """Запрещает скрыто сальдировать приход и расход одной позиции внутри проведения."""


class StockPostingExecutionTimeError(InvalidStockPostingValueError):
    """Запрещает проведение раньше фактического исполнения."""
