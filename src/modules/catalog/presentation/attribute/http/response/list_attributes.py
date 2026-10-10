from pydantic import BaseModel
from uuid import UUID


class ListAttributeItemResponse(BaseModel):
    """Одна строка конкретного списка определений."""

    id: UUID
    code: str
    label: str | None
    revision: int
    option_count: int


class ListAttributesResponse(BaseModel):
    """Страница результата list_attributes."""

    items: tuple[ListAttributeItemResponse, ...]
    total: int
    page: int
    page_size: int
