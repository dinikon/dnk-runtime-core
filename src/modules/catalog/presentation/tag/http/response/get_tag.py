from pydantic import BaseModel
from uuid import UUID


class GetTagResponse(BaseModel):
    """Карточка справочника в сценарии get_tag, без locale fallback."""

    id: UUID
    label: str | None
    revision: int
    locales: tuple[str, ...]
