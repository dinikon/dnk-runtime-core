from enum import StrEnum


class RuntimeSchemaFieldType(StrEnum):
    UUID = "uuid"
    STRING = "string"
    LONG_TEXT = "long_text"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    DECIMAL = "decimal"
    JSON = "json"
