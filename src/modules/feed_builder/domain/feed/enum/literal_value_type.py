from enum import StrEnum


class LiteralValueType(StrEnum):
    """Задаёт строгий тип скалярного литерала условия."""

    UUID = "uuid"
    STRING = "string"
    BOOLEAN = "boolean"
