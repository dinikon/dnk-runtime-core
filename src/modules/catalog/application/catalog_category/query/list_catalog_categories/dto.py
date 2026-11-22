from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CatalogCategoryRowDTO:
    """Узел дерева с исходным и запрошенным названием."""

    id: UUID
    parent_id: UUID | None
    source_locale: str
    name: str | None
    source_name: str
    is_default: bool


@dataclass(frozen=True, slots=True)
class ListCatalogCategoriesResultDTO:
    """Узлы дерева категорий текущего каталога."""

    items: tuple[CatalogCategoryRowDTO, ...]
