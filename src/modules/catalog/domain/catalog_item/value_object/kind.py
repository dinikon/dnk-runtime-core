from enum import StrEnum


class CatalogItemKind(StrEnum):
    """Роли центральной товарной модели."""

    SIMPLE = "simple"
    VARIABLE = "variable"
    VARIANT = "variant"


class CatalogItemStatus(StrEnum):
    """Локальный жизненный цикл карточки."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
