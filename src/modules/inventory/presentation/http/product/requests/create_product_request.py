from uuid import UUID

from pydantic import BaseModel


class CreateProductRequestSchema(BaseModel):
    """Pydantic-схема тела запроса создания товара."""

    sku: str
    product_name: str
    description: str | None = None
    category_id: UUID | None = None


__all__ = ["CreateProductRequestSchema"]
