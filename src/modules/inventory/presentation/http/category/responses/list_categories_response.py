from pydantic import BaseModel

from .category_response import CategoryResponseSchema


class ListCategoriesResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа со страницей категорий."""

    items: list[CategoryResponseSchema]
    limit: int
    offset: int
    count: int


__all__ = ["ListCategoriesResponseSchema"]
