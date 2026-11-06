from src.modules.inventory.domain.error import InventoryError


class ValuationLayerError(InventoryError):
    """Базовая ошибка фиксации первоначальной стоимости поступления."""


class InvalidValuationLayerValueError(ValuationLayerError):
    """Отклоняет нетипизированные или несогласованные собственные данные слоя."""


class InvalidValuationLayerSourceError(ValuationLayerError):
    """Отклоняет некорректные ссылки на проведение, запись и исходную позицию."""


class InvalidCostBasisError(ValuationLayerError):
    """Требует положительное количество и конечную неотрицательную полную стоимость."""


class ValuationLayerTimeError(InvalidValuationLayerValueError):
    """Требует aware-время в UTC и регистрацию слоя не раньше исходного поступления."""
