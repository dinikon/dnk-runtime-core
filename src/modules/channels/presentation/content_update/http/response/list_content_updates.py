from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ContentUpdateSummaryResponse(BaseModel):
    """Показывает строку истории операций."""

    id: UUID
    status: str
    created_at: datetime
    total: int


class ListContentUpdatesResponse(BaseModel):
    """Возвращает ограниченную историю текущего автора."""

    items: list[ContentUpdateSummaryResponse]
