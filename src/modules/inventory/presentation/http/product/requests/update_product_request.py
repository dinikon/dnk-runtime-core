from uuid import UUID

from pydantic import BaseModel


class UpdateProductRequestSchema(BaseModel):
    """Pydantic-схема тела запроса обновления товара."""

    sku: str
    product_name: str
    description: str | None = None
    category_id: UUID | None = None


__all__ = ["UpdateProductRequestSchema"]
