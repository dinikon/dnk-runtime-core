from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProductResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа с одним товаром."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    sku: str
    product_name: str
    description: str | None
    category_id: UUID | None


__all__ = ["ProductResponseSchema"]
