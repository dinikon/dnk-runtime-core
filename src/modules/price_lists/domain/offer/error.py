from src.modules.shared.domain.domain_error import DomainError


class InvalidOfferValueError(DomainError):
    """Невалидное значение предложения."""


class OfferNotFoundError(DomainError):
    """Предложение не найдено в текущем tenant."""


__all__ = ["InvalidOfferValueError", "OfferNotFoundError"]
