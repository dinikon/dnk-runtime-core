from enum import StrEnum


class CountType(StrEnum):
    """Выбирает весь склад или явно перечисленные локации в рамках одного владельца."""

    FULL = "FULL"
    PARTIAL = "PARTIAL"
