from uuid import UUID
from pydantic import BaseModel


class ContentBlockListItemResponse(BaseModel):
    """Строка HTTP-списка list_content_blocks."""

    id: UUID
    code: str
    is_system: bool
    revision: int
    label: str | None
    locales: tuple[str, ...]
    value_type: str


class ListContentBlocksResponse(BaseModel):
    """Ответ HTTP-сценария list_content_blocks."""

    items: tuple[ContentBlockListItemResponse, ...]
    total: int
    page: int
    page_size: int
