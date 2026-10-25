from src.modules.shared.domain.domain_error import DomainError


class SalesError(DomainError):
    """Нарушение правил обращения или продажи."""


class SalesNotFoundError(SalesError):
    """Объект отсутствует в текущем tenant."""


class SalesConflictError(SalesError):
    """Состояние или версия объекта изменились."""
