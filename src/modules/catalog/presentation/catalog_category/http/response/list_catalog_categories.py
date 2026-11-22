from uuid import UUID
from pydantic import BaseModel


class CatalogCategoryRowResponse(BaseModel):
    """Передаёт локализованное название и родителя категории."""

    id: UUID
    parent_id: UUID | None
    source_locale: str
    source_name: str
    name: str | None
    is_default: bool


class ListCatalogCategoriesResponse(BaseModel):
    """Возвращает узлы дерева для выбранного языка."""

    items: tuple[CatalogCategoryRowResponse, ...]
