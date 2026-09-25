from src.modules.shared.domain.domain_error import DomainError


class InvalidContactPointBindingError(DomainError):
    """Ошибка конкретной строки контактного массива."""

    def __init__(self, message: str, array: str, index: int, field: str = "value"):
        super().__init__(message)
        self.array, self.index, self.field = array, index, field


class InvalidContactPointTargetError(DomainError):
    """Некорректная ссылка на объект-владелец."""


__all__ = ["InvalidContactPointBindingError", "InvalidContactPointTargetError"]
