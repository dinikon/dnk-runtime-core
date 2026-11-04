from enum import StrEnum


class StockTransferStatus(StrEnum):
    """Разделяет редактируемый черновик, подтверждённый план и отменённый черновик перемещения."""

    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
