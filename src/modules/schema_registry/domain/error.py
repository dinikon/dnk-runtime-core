from src.modules.shared import DomainError


class ObjectNotFoundError(DomainError):
    pass


class ObjectAlreadyDeletedError(DomainError):
    pass


class FieldNotFoundError(DomainError):
    pass


class FieldAlreadyExistsError(DomainError):
    pass


class ObjectNameAlreadyExistsError(DomainError):
    pass


class InvalidFieldOperationError(DomainError):
    pass


class InvalidValueObjectError(DomainError):
    pass
