from enum import StrEnum


class CatalogSourcePath(StrEnum):
    """Задаёт закрытый набор логических источников Catalog для полей Feed."""

    TITLE = "item.title"
    DESCRIPTION = "item.description"
    SKU = "item.sku"
    REGULAR_PRICE = "item.regular_price"
