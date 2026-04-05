from src.modules.shared import DomainError


class SchemaRegistryError(DomainError):
    pass


class ObjectNotFoundError(SchemaRegistryError):
    pass


class ObjectAlreadyDeletedError(SchemaRegistryError):
    pass


class FieldNotFoundError(SchemaRegistryError):
    pass


class FieldAlreadyExistsError(SchemaRegistryError):
    pass


class ObjectNameAlreadyExistsError(SchemaRegistryError):
    pass


class InvalidFieldOperationError(SchemaRegistryError):
    pass


class InvalidValueObjectError(SchemaRegistryError):
    pass


class SeedValidationError(SchemaRegistryError):
    pass


class UnsupportedSchemaBackendError(SchemaRegistryError):
    pass


class UnsupportedSchemaChangeError(SchemaRegistryError):
    pass
