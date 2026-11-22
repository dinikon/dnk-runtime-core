from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CatalogCategoryRowDTO:
    """Узел дерева с запрошенным и резервным названием."""

    id: UUID
    parent_id: UUID | None
    name: str | None
    fallback_locale: str
    fallback_name: str
    is_default: bool


@dataclass(frozen=True, slots=True)
class ListCatalogCategoriesResultDTO:
    """Узлы дерева категорий текущего каталога."""

    items: tuple[CatalogCategoryRowDTO, ...]
