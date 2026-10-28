from enum import StrEnum


class CatalogItemKind(StrEnum):
    """Роли карточки и её продаваемых позиций."""

    SIMPLE = "simple"
    VARIABLE = "variable"
    VARIANT = "variant"
