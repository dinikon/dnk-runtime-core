from enum import StrEnum


class ValueDefinitionKind(StrEnum):
    """Различает способы определения значения поля."""

    SOURCE = "SOURCE"
    MANUAL = "MANUAL"
    MONEY = "MONEY"
