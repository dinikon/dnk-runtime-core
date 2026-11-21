from enum import StrEnum


class ShipmentStatus(StrEnum):
    """Разделяет черновик, подтверждение, частичную/полную отгрузку и отмену черновика."""

    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    PARTIALLY_SHIPPED = "PARTIALLY_SHIPPED"
    SHIPPED = "SHIPPED"
    CANCELLED = "CANCELLED"
