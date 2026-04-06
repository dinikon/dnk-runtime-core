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


class DataSourceAlreadyExistsError(SchemaRegistryError):
    def __init__(self, tenant_id: str):
        super().__init__(
            f"Schema registry datasource already exists for tenant '{tenant_id}'."
        )


class DataSourceNotFoundError(SchemaRegistryError):
    def __init__(self, tenant_id: str):
        super().__init__(
            f"Schema registry datasource was not found for tenant '{tenant_id}'."
        )


class PhysicalSchemaAlreadyExistsError(SchemaRegistryError):
    def __init__(self, schema_name: str):
        super().__init__(f"PostgreSQL schema '{schema_name}' already exists.")


class PhysicalSchemaNotFoundError(SchemaRegistryError):
    def __init__(self, schema_name: str):
        super().__init__(f"PostgreSQL schema '{schema_name}' was not found.")


class SchemaRegistryMetadataInconsistentError(SchemaRegistryError):
    pass


class UnsupportedSchemaBackendError(SchemaRegistryError):
    pass


class UnsupportedSchemaChangeError(SchemaRegistryError):
    pass
