from enum import StrEnum


class CatalogItemStatus(StrEnum):
    """Локальный жизненный цикл самостоятельного товара."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
