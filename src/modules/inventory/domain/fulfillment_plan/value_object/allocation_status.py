from enum import StrEnum


class FulfillmentAllocationStatus(StrEnum):
    """Разделяет намерение, подтверждение резервом и накопленное исполнение распределения."""

    PLANNED = "PLANNED"
    CONFIRMED = "CONFIRMED"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
