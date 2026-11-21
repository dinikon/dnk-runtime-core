from enum import StrEnum


class MoneyValueMode(StrEnum):
    """Определяет источник, расчёт или ручное заполнение денег."""

    SOURCE = "SOURCE"
    CALCULATED = "CALCULATED"
    MANUAL = "MANUAL"
