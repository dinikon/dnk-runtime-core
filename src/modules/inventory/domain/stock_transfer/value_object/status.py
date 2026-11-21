from enum import StrEnum


class StockTransferStatus(StrEnum):
    """Разделяет черновик, подтверждение, исполнение, завершение и отмену черновика перемещения."""

    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
