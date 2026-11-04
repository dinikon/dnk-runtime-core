from enum import StrEnum


class ShipmentStatus(StrEnum):
    """Разделяет редактируемый черновик, подтверждённый план и отмену черновика."""

    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
