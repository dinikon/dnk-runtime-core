from enum import StrEnum


class LogicalOperator(StrEnum):
    """Перечисляет способы объединения условий."""

    ALL = "ALL"
    ANY = "ANY"
    NOT = "NOT"
