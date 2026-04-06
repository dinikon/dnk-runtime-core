from enum import Enum


class SqlTypePresetEnum(str, Enum):
    TEXT = "text"
    VARCHAR_255 = "varchar_255"
    INTEGER = "integer"
    BIGINT = "bigint"
    NUMERIC_14_2 = "numeric_14_2"
    BOOLEAN = "boolean"
    DATE = "date"
    TIMESTAMP = "timestamp"
    JSONB = "jsonb"
    UUID = "uuid"
