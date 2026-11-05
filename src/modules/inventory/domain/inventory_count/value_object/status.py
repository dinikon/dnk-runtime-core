from enum import StrEnum


class InventoryCountStatus(StrEnum):
    """Разделяет черновик, подтверждённый план, запущенную проверку и отмену черновика."""

    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    CANCELLED = "CANCELLED"
