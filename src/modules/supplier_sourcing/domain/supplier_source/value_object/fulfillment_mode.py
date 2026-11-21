from enum import StrEnum


class SupplierFulfillmentMode(StrEnum):
    """Поддерживаемые источником маршруты поставки."""

    DROPSHIP = "DROPSHIP"
    PURCHASE_TO_WAREHOUSE = "PURCHASE_TO_WAREHOUSE"
