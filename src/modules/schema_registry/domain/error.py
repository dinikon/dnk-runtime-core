from src.modules.shared import DomainError


class SchemaRegistryError(DomainError):
    """Базовая доменная ошибка модуля schema_registry."""

    pass


class ObjectNotFoundError(SchemaRegistryError):
    """Ошибка поиска отсутствующего runtime-объекта metadata."""

    pass


class ObjectAlreadyDeletedError(SchemaRegistryError):
    """Ошибка операции над уже удаленным runtime-объектом."""

    pass


class FieldNotFoundError(SchemaRegistryError):
    """Ошибка поиска отсутствующего поля runtime-объекта."""

    pass


class RelationNotFoundError(SchemaRegistryError):
    """Ошибка поиска отсутствующей relation metadata."""

    pass


class FieldAlreadyExistsError(SchemaRegistryError):
    """Ошибка добавления поля с уже занятым именем."""

    pass


class ObjectNameAlreadyExistsError(SchemaRegistryError):
    """Ошибка конфликта singular/plural имени runtime-объекта."""

    pass


class InvalidFieldOperationError(SchemaRegistryError):
    """Ошибка неподдержанной или запрещенной операции над полем."""

    pass


class InvalidObjectOperationError(SchemaRegistryError):
    """Ошибка неподдержанной или запрещенной операции над runtime-объектом."""

    pass


class InvalidRelationOperationError(SchemaRegistryError):
    """Ошибка неподдержанной или запрещенной операции над relation metadata."""

    pass


class InvalidValueObjectError(SchemaRegistryError):
    """Ошибка валидации value object в домене schema_registry."""

    pass


class SeedValidationError(SchemaRegistryError):
    """Ошибка валидации seed-спеки runtime-схемы."""

    pass


class DataSourceAlreadyExistsError(SchemaRegistryError):
    """Ошибка повторного создания datasource metadata для tenant."""

    def __init__(self, tenant_id: str) -> None:
        """Формирует сообщение с tenant_id, у которого datasource уже существует."""
        super().__init__(
            f"Schema registry datasource already exists for tenant '{tenant_id}'."
        )


class DataSourceNotFoundError(SchemaRegistryError):
    """Ошибка отсутствия datasource metadata для tenant."""

    def __init__(self, tenant_id: str) -> None:
        """Формирует сообщение с tenant_id, у которого не найден datasource."""
        super().__init__(
            f"Schema registry datasource was not found for tenant '{tenant_id}'."
        )


class PhysicalSchemaAlreadyExistsError(SchemaRegistryError):
    """Ошибка создания физической PostgreSQL-схемы, которая уже существует."""

    def __init__(self, schema_name: str) -> None:
        """Формирует сообщение с именем уже существующей схемы."""
        super().__init__(f"PostgreSQL schema '{schema_name}' already exists.")


class PhysicalSchemaNotFoundError(SchemaRegistryError):
    """Ошибка отсутствия физической PostgreSQL-схемы."""

    def __init__(self, schema_name: str) -> None:
        """Формирует сообщение с именем отсутствующей схемы."""
        super().__init__(f"PostgreSQL schema '{schema_name}' was not found.")


class SchemaRegistryMetadataInconsistentError(SchemaRegistryError):
    """Ошибка несогласованности metadata datasource и runtime-объектов."""

    pass


class UnsupportedSchemaBackendError(SchemaRegistryError):
    """Ошибка использования schema_registry с неподдержанным backend-хранилищем."""

    pass


class UnsupportedSchemaChangeError(SchemaRegistryError):
    """Ошибка неподдержанного или небезопасного изменения физической схемы."""

    pass


class RuntimeObjectNotFoundError(SchemaRegistryError):
    """Ошибка отсутствия runtime descriptor объекта для tenant."""

    def __init__(self, *, tenant_id: str, object_name: str) -> None:
        """Формирует сообщение с tenant_id и именем runtime-объекта."""
        super().__init__(
            "Runtime object " f"'{object_name}' was not found for tenant '{tenant_id}'."
        )


class RuntimeObjectDescriptorError(SchemaRegistryError):
    """Ошибка построения некорректного runtime descriptor из metadata."""

    pass
