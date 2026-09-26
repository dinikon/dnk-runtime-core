from src.modules.shared.domain.domain_error import DomainError


class InvalidCrmContactPointError(DomainError):
    """Ошибка строки контактных данных, переведённая адаптером CRM."""

    def __init__(self, message: str, array: str, index: int, field: str):
        super().__init__(message)
        self.array, self.index, self.field = array, index, field


__all__ = ["InvalidCrmContactPointError"]
