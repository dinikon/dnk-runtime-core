from __future__ import annotations

from src.modules.shared.domain.errors import DomainError


class RuntimeSchemaDomainError(DomainError):
    """Base runtime-schema domain error."""


class InvalidSchemaNameFormatError(RuntimeSchemaDomainError):
    def __init__(self, value: str):
        super().__init__(f"Invalid data_source name format: '{value}'")


class InvalidSchemaIdError(RuntimeSchemaDomainError):
    def __init__(self, value: object):
        super().__init__(
            f"SchemaIdVO value must be UUID or UUID string, got: {type(value).__name__}"
        )


__all__ = [
    "InvalidSchemaIdError",
    "InvalidSchemaNameFormatError",
    "RuntimeSchemaDomainError",
]
