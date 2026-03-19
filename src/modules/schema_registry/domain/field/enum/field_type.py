from enum import StrEnum, Enum


class FieldTypeEnum(str, Enum):
    TEXT = "text"
    INT = "int"
    DECIMAL = "decimal"
    BOOL = "bool"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"
    UUID = "uuid"
    SELECT = "select"
    MULTISELECT = "multiselect"
