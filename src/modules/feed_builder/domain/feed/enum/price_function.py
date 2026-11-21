from enum import StrEnum


class PriceFunction(StrEnum):
    """Перечисляет разрешённые функции выражений."""

    MIN = "MIN"
    MAX = "MAX"
    ABS = "ABS"
