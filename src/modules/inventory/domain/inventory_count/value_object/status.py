from enum import StrEnum


class InventoryCountStatus(StrEnum):
    """Разделяет черновик, план, пересчёт, зафиксированный результат, завершение и отмену черновика."""

    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COUNTED = "COUNTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
