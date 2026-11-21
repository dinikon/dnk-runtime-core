from enum import StrEnum


class FulfillmentSourceKind(StrEnum):
    """Перечисляет реализованные виды источников ручного плана исполнения."""

    OWN_WAREHOUSE = "OWN_WAREHOUSE"
    SUPPLIER_DROPSHIP = "SUPPLIER_DROPSHIP"
