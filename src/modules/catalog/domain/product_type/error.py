from src.modules.shared.domain.domain_error import DomainError


class InvalidProductTypeError(DomainError):
    """Тип товара или его схема нарушают доменные правила."""


class ProductTypeNotFoundError(DomainError):
    """Тип товара отсутствует в текущем tenant."""


class ProductTypeConflictError(DomainError):
    """Тип нельзя изменить или удалить из-за версии либо использования."""
