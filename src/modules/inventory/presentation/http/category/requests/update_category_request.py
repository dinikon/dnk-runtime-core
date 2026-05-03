from uuid import UUID

from pydantic import BaseModel


class UpdateCategoryRequestSchema(BaseModel):
    """Pydantic-схема тела запроса обновления категории товаров."""

    name: str
    parent_category_id: UUID | None = None


__all__ = ["UpdateCategoryRequestSchema"]
