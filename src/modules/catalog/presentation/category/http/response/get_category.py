from pydantic import BaseModel
from uuid import UUID


class GetCategoryResponse(BaseModel):
    """Карточка справочника в сценарии get_category, без locale fallback."""

    id: UUID
    label: str | None
    revision: int
    locales: tuple[str, ...]
    parent_id: UUID | None
    child_count: int
