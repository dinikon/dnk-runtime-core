from uuid import UUID

from pydantic import BaseModel


class CreateCategoryRequestSchema(BaseModel):
    """Pydantic-схема тела запроса создания категории товаров."""

    name: str
    parent_category_id: UUID | None = None


__all__ = ["CreateCategoryRequestSchema"]
