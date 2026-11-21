from enum import StrEnum


class ArithmeticOperator(StrEnum):
    """Задаёт структуру арифметической операции без её исполнения."""

    ADD = "ADD"
    SUBTRACT = "SUBTRACT"
    MULTIPLY = "MULTIPLY"
    DIVIDE = "DIVIDE"
    NEGATE = "NEGATE"
