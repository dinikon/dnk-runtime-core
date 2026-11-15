from enum import StrEnum


class StockOperationType(StrEnum):
    """Описывает поддержанные правила проведения, независимо от статусов документов."""

    RETURN = "RETURN"
    RECEIPT = "RECEIPT"
    ISSUE = "ISSUE"
    WRITE_OFF = "WRITE_OFF"
    STATUS_CHANGE = "STATUS_CHANGE"
    INTERNAL_MOVE = "INTERNAL_MOVE"
    ADJUSTMENT = "ADJUSTMENT"
