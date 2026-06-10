from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BroadcastResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа с одним broadcast."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    title: str
    description: str | None
    status: str


__all__ = ["BroadcastResponseSchema"]
