from src.modules.shared.domain.domain_error import DomainError


class InvalidWarehouseTitleError(DomainError):
    """Название склада пустое или превышает допустимую длину."""


class WarehouseSelfParentError(DomainError):
    """Склад не может быть собственным родителем."""
