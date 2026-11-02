from src.modules.shared.domain.domain_error import DomainError


class InventoryError(DomainError):
    """Базовая ошибка складского контекста."""


class InvalidUomCodeError(InventoryError):
    """Сообщает о недопустимом коде единицы учёта."""


class InvalidPackagingValueError(InventoryError):
    """Сообщает о некорректном коде или названии тары."""


class UnknownUomError(InventoryError):
    """Сообщает об отсутствии единицы в системном справочнике."""


class InvalidUomDefinitionError(InventoryError):
    """Сообщает о некорректном системном определении единицы."""


class IncompatibleUomError(InventoryError):
    """Запрещает пересчёт между разными физическими размерностями."""


class InvalidQuantityError(InventoryError):
    """Сообщает о некорректном неотрицательном количестве."""


class UomConversionError(InventoryError):
    """Сообщает, что количество нельзя точно выразить в выбранной единице."""
