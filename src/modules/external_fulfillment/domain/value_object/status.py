from enum import StrEnum


class SupplierFulfillmentOrderStatus(StrEnum):
    """Состояние заявки на прямую поставку."""

    DRAFT = "DRAFT"
    REQUESTED = "REQUESTED"
    CONFIRMED = "CONFIRMED"
    PARTIALLY_CONFIRMED = "PARTIALLY_CONFIRMED"
    REJECTED = "REJECTED"
    SHIPPED = "SHIPPED"
