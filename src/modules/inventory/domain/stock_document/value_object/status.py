from enum import StrEnum


class StockDocumentStatus(StrEnum):
    """Разделяет черновик, подтверждённый план, накопленный прогресс, завершение и отмену."""

    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
