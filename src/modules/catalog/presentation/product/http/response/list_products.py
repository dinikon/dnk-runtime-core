from uuid import UUID
from pydantic import BaseModel


class ProductListItemResponse(BaseModel):
    """Строка HTTP-списка list_products."""

    id: UUID
    kind: str
    product_type_id: UUID
    revision: int
    schema_version: int
    content: dict[str, str] | None
    locales: tuple[str, ...]
    variant_id: UUID
    virtual: bool
    downloadable: bool
    variant_content: dict[str, str] | None
    variant_locales: tuple[str, ...]


class ListProductsResponse(BaseModel):
    """Ответ HTTP-сценария list_products."""

    items: tuple[ProductListItemResponse, ...]
    total: int
    page: int
    page_size: int
