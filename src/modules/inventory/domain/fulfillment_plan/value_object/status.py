from enum import StrEnum


class FulfillmentPlanStatus(StrEnum):
    """Разделяет планирование, подтверждение резервами, исполнение и отмену."""

    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    AWAITING_ALLOCATION = "AWAITING_ALLOCATION"
    PARTIALLY_CONFIRMED = "PARTIALLY_CONFIRMED"
    CONFIRMED = "CONFIRMED"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
