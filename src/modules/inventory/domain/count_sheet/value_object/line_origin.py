from enum import StrEnum


class CountLineOrigin(StrEnum):
    """Различает позицию учётного основания и найденные измерения без учётной позиции."""

    BASELINE = "BASELINE"
    FOUND = "FOUND"
