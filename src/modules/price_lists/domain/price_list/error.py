from src.modules.shared.domain.domain_error import DomainError


class PriceListValidationError(DomainError):
    """Некорректные настройки прайса."""


class MappingValidationError(PriceListValidationError):
    """Источник или mapping не позволяют получить корректные предложения."""


class PriceListNotFoundError(DomainError):
    """Прайс не найден в текущем tenant."""


class PriceListStateConflict(DomainError):
    """Текущее состояние запрещает действие."""


__all__ = [
    "PriceListValidationError",
    "MappingValidationError",
    "PriceListNotFoundError",
    "PriceListStateConflict",
]
