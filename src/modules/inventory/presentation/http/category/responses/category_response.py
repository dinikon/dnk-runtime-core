from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CategoryResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа с одной категорией товаров."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    parent_category_id: UUID | None


__all__ = ["CategoryResponseSchema"]
