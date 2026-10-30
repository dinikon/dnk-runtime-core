from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RefreshPublicationStockRequest(BaseModel):
    """Пустой список выбирает все пары текущей группы."""

    model_config = ConfigDict(extra="forbid")
    publication_ids: tuple[UUID, ...] = Field(default=(), max_length=1000)
