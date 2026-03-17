from __future__ import annotations

from enum import StrEnum

FIELD_NAME_MAX_LENGTH = 63


class DataSourceType(StrEnum):
    POSTGRESQL = "postgresql"


class ObjectOwnershipKind(StrEnum):
    MODULE = "module"
    CUSTOM = "custom"


class FieldType(StrEnum):
    PK = "PK"
    STRING = "STRING"
    LARGE_TEXT = "LARGE_TEXT"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"
    SELECT = "SELECT"
    MULTISELECT = "MULTISELECT"


__all__ = [
    "DataSourceType",
    "FIELD_NAME_MAX_LENGTH",
    "FieldType",
    "ObjectOwnershipKind",
]
