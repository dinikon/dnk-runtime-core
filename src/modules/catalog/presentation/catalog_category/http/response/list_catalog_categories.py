from uuid import UUID
from pydantic import BaseModel


class CatalogCategoryRowResponse(BaseModel):
    """Передаёт локализованное название и родителя категории."""

    id: UUID
    parent_id: UUID | None
    name: str | None
    fallback_locale: str
    fallback_name: str
    is_default: bool


class ListCatalogCategoriesResponse(BaseModel):
    """Возвращает узлы дерева для выбранного языка."""

    items: tuple[CatalogCategoryRowResponse, ...]
