from src.modules.shared.domain.domain_error import DomainError


class InventoryError(DomainError):
    """Базовая ошибка складского контекста."""


class InvalidUomCodeError(InventoryError):
    """Сообщает о недопустимом коде единицы учёта."""


class InvalidPackagingValueError(InventoryError):
    """Сообщает о некорректном коде или названии тары."""
