from src.modules.shared import DomainError


class RuntimeDataError(DomainError):
    pass


class RuntimeDataValidationError(RuntimeDataError):
    pass


class RuntimeDataObjectNotFoundError(RuntimeDataError):
    pass


class RuntimeDataFilterError(RuntimeDataError):
    pass


class RuntimeDataPolicyError(RuntimeDataError):
    pass


class RuntimeDataPersistenceError(RuntimeDataError):
    pass
