from __future__ import annotations

from uuid import UUID

from src.modules.shared.domain.errors import DomainError


class InvalidDataSourceTypeError(DomainError):
    def __init__(self, value: str):
        super().__init__(
            f"Invalid data source type '{value}'. Only 'postgresql' is supported."
        )


class InvalidDataSourceSchemaError(DomainError):
    def __init__(self, value: str):
        super().__init__(f"Invalid data source schema '{value}'. UUID is required.")


class InvalidObjectOwnershipKindError(DomainError):
    def __init__(self, value: str):
        super().__init__(
            f"Invalid object ownership kind '{value}'. Use 'module' or 'custom'."
        )


class ObjectOwnershipKindImmutableError(DomainError):
    def __init__(self):
        super().__init__("Object ownership_kind is immutable after creation.")


class InvalidFieldNameError(DomainError):
    def __init__(self, value: str):
        super().__init__(
            "Field name must be snake_case, latin letters/digits/underscore, "
            f"max 63 chars. Got: '{value}'."
        )


class InvalidFieldTypeError(DomainError):
    def __init__(self, value: str):
        super().__init__(f"Invalid field type '{value}'.")


class DataSourceNotFoundError(DomainError):
    def __init__(self, data_source_id: UUID):
        super().__init__(f"Data source '{data_source_id}' was not found.")


class ObjectMetadataNotFoundError(DomainError):
    def __init__(self, identifier: str):
        super().__init__(f"Object metadata '{identifier}' was not found.")


class FieldMetadataNotFoundError(DomainError):
    def __init__(self, field_metadata_id: UUID):
        super().__init__(f"Field metadata '{field_metadata_id}' was not found.")


__all__ = [
    "DataSourceNotFoundError",
    "FieldMetadataNotFoundError",
    "InvalidDataSourceSchemaError",
    "InvalidDataSourceTypeError",
    "InvalidFieldNameError",
    "InvalidFieldTypeError",
    "InvalidObjectOwnershipKindError",
    "ObjectMetadataNotFoundError",
    "ObjectOwnershipKindImmutableError",
]
