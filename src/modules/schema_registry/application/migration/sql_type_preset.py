from enum import Enum


class SqlTypePresetEnum(str, Enum):
    """Канонические SQL-типы, которыми оперирует schema_registry diff."""

    TEXT = "text"
    VARCHAR_255 = "varchar_255"
    INTEGER = "integer"
    BIGINT = "bigint"
    NUMERIC_14_2 = "numeric_14_2"
    BOOLEAN = "boolean"
    DATE = "date"
    TIMESTAMP = "timestamp"
    TIMESTAMPTZ = "timestamptz"
    JSONB = "jsonb"
    UUID = "uuid"
