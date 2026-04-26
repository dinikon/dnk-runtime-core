from pydantic import BaseModel

from .product_response import ProductResponseSchema


class ListProductsResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа со страницей товаров."""

    items: list[ProductResponseSchema]
    limit: int
    offset: int
    count: int


__all__ = ["ListProductsResponseSchema"]
