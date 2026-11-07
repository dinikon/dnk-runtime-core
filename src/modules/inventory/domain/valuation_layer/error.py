from src.modules.inventory.domain.error import InventoryError


class ValuationLayerError(InventoryError):
    """Базовая ошибка фиксации и потребления стоимости поступления."""


class InvalidValuationLayerValueError(ValuationLayerError):
    """Отклоняет нетипизированные или несогласованные собственные данные слоя."""


class InvalidValuationLayerReceiptSnapshotError(InvalidValuationLayerValueError):
    """Отклоняет некорректный снимок первоначального стоимостного основания слоя."""


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
