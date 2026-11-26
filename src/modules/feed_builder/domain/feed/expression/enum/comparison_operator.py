from enum import StrEnum


class ComparisonOperator(StrEnum):
    """Перечисляет операции сравнения и принадлежности."""

    EQ = "EQ"
    NE = "NE"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    IN = "IN"
    NOT_IN = "NOT_IN"
    CONTAINS = "CONTAINS"
