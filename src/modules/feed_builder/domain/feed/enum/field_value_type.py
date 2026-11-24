from enum import StrEnum


class FieldValueType(StrEnum):
    """Определяет тип значения пользовательского поля."""

    STRING = "string"
    TEXT = "text"
    MONEY = "money"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    CATEGORY = "category"
