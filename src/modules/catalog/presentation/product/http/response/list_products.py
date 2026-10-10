from pydantic import BaseModel
from uuid import UUID


class ProductListItemResponse(BaseModel):
    """Одна строка товара, независимо от числа принадлежащих позиций."""

    id: UUID
    kind: str
    product_type_id: UUID
    revision: int
    schema_version: int
    content: dict[str, str] | None
    locales: tuple[str, ...]
    title: str | None
    variant_count: int


class ListProductsResponse(BaseModel):
    """Страница результата list_products без повторов Product."""

    items: tuple[ProductListItemResponse, ...]
    total: int
    page: int
    page_size: int
