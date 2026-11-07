from src.modules.inventory.domain.error import InventoryError


class ValuationLayerError(InventoryError):
    """Базовая ошибка фиксации, переноса и потребления стоимости слоя."""


class InvalidValuationLayerValueError(ValuationLayerError):
    """Отклоняет нетипизированные или несогласованные собственные данные слоя."""


class InvalidValuationLayerReceiptSnapshotError(InvalidValuationLayerValueError):
    """Отклоняет некорректное основание закупочного прихода."""


class InvalidValuationLayerBasisSnapshotError(InvalidValuationLayerValueError):
    """Отклоняет некорректное первоначальное основание стоимостного слоя."""


class InvalidValuationLayerTransferOriginError(InvalidValuationLayerValueError):
    """Отклоняет некорректные ссылки и дату происхождения производного слоя."""


class ValuationLayerMovementMismatchError(ValuationLayerError):
    """Отклоняет перенос стоимости из слоя, несовместимого с парой INTERNAL_MOVE."""


class InvalidValuationLayerMovementConsumptionSnapshotError(
    InvalidValuationLayerValueError
):
    """Отклоняет несогласованный результат потребления слоя по паре INTERNAL_MOVE."""


class InvalidValuationLayerSourceError(ValuationLayerError):
    """Отклоняет некорректные ссылки на проведение, запись и исходную позицию."""


class InvalidCostBasisError(ValuationLayerError):
    """Требует положительное количество и конечную неотрицательную полную стоимость."""


class ValuationLayerTimeError(InvalidValuationLayerValueError):
    """Требует aware-время в UTC и последовательную хронологию слоя."""


class ValuationLayerVersionConflictError(ValuationLayerError):
    """Отклоняет потребление по устаревшей версии слоя."""


class ValuationLayerConsumptionError(ValuationLayerError):
    """Отклоняет неположительное потребление или превышение остатка слоя."""


class ValuationLayerIssueMismatchError(ValuationLayerError):
    """Отклоняет расход другого товара, владельца, склада, единицы или исходной позиции слоя."""


class InvalidValuationLayerConsumptionSnapshotError(InvalidValuationLayerValueError):
    """Отклоняет несогласованный результат потребления слоя по конкретному расходу."""


class InvalidValuationLayerFifoSnapshotError(InvalidValuationLayerValueError):
    """Отклоняет некорректное состояние кандидата FIFO."""


class InvalidValuationIssueAllocationError(ValuationLayerError):
    """Требует номинальный слой, положительную часть расхода и строгую ожидаемую версию."""


class InvalidStockIssueFifoPlanError(ValuationLayerError):
    """Отклоняет некорректный пул кандидатов или назначения, не соответствующие FIFO."""


class InsufficientValuationFifoQuantityError(ValuationLayerConsumptionError):
    """Не позволяет построить частичный FIFO-план при недостаточном количестве слоёв."""


class ValuationFifoStateConflictError(ValuationLayerError):
    """Отклоняет невыбранный слой или его состояние, отличающееся от основания плана."""
