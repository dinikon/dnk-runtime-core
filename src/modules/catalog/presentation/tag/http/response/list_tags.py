from pydantic import BaseModel
from uuid import UUID


class TagListItemResponse(BaseModel):
    """Строка отдельной проекции list_tags."""

    id: UUID
    label: str | None
    revision: int


class ListTagsResponse(BaseModel):
    """Стабильно упорядоченная страница сценария list_tags."""

    items: tuple[TagListItemResponse, ...]
    total: int
    page: int
    page_size: int
