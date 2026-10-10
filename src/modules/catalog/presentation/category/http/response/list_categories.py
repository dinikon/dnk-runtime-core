from pydantic import BaseModel
from uuid import UUID


class CategoryListItemResponse(BaseModel):
    """Строка отдельной проекции list_categories."""

    id: UUID
    label: str | None
    revision: int
    parent_id: UUID | None
    child_count: int


class ListCategoriesResponse(BaseModel):
    """Стабильно упорядоченная страница сценария list_categories."""

    items: tuple[CategoryListItemResponse, ...]
    total: int
    page: int
    page_size: int
