from src.modules.shared.domain.domain_error import DomainError


class InvalidContactPointError(DomainError):
    """Некорректное значение точки контакта."""

    def __init__(self, message: str, field: str = "value"):
        super().__init__(message)
        self.field = field


class ContactPointNotFoundError(DomainError):
    """Точка контакта отсутствует в tenant."""


__all__ = ["InvalidContactPointError", "ContactPointNotFoundError"]
