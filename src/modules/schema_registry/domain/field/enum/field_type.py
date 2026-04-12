from enum import Enum


class FieldTypeEnum(str, Enum):
    """Доменный список типов полей runtime-объектов."""

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
