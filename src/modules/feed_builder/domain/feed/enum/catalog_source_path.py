from enum import StrEnum


class CatalogSourcePath(StrEnum):
    """Задаёт закрытый набор логических источников Catalog для полей Feed."""

    TITLE = "item.title"
    DESCRIPTION = "item.description"
    DESCRIPTION_HTML = "item.description_html"
    SKU = "item.sku"
    REGULAR_PRICE = "item.regular_price"
    STOCK_QUANTITY = "item.stock_quantity"
    IN_STOCK = "item.in_stock"
