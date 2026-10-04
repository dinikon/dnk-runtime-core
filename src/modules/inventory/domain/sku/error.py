from src.modules.shared.domain.domain_error import DomainError


class InvalidSkuCodeError(DomainError):
    """Код SKU имеет недопустимый тип, длину или управляющие символы."""


class InvalidSkuTitleError(DomainError):
    """Название учётной позиции пустое или превышает допустимую длину."""


class SkuCodeAlreadyExistsError(DomainError):
    """Код SKU уже занят в текущем tenant."""


class SkuIdentifierAlreadyExistsError(DomainError):
    """Идентификатор SKU уже существует в текущем tenant."""


class SkuNotFoundError(DomainError):
    """SKU отсутствует в текущем tenant."""
