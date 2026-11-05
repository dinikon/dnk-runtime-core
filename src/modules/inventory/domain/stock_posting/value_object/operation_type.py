from enum import StrEnum


class StockOperationType(StrEnum):
    """Описывает поддержанные правила проведения, независимо от статусов документов."""

    RECEIPT = "RECEIPT"
    ISSUE = "ISSUE"
    INTERNAL_MOVE = "INTERNAL_MOVE"
    ADJUSTMENT = "ADJUSTMENT"
