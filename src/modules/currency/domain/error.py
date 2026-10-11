from src.modules.shared.domain.domain_error import DomainError


class InvalidExchangeRateError(DomainError):
    """Коэффициент не является положительным конечным NUMERIC(38,18)."""


class InvalidExchangeRateSnapshotError(DomainError):
    """Снимок пуст, несогласован или содержит повторяющиеся валюты."""


class OlderExchangeRateSnapshotError(DomainError):
    """Запоздавшая проверка не может заменить более новое состояние книги."""
