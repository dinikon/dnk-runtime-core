from uuid import UUID
from pydantic import BaseModel


class SchemaBlockResponse(BaseModel):
    """HTTP-представление одной связи схемы для данного чтения."""

    block_id: UUID
    code: str
    value_type: str
    label: str | None
    scope: str
    required: bool
    position: int


class ProductTypeListItemResponse(BaseModel):
    """Строка HTTP-списка list_product_types."""

    id: UUID
    code: str
    is_system: bool
    revision: int
    label: str | None
    locales: tuple[str, ...]
    schema_version: int
    blocks: tuple[SchemaBlockResponse, ...]


class ListProductTypesResponse(BaseModel):
    """Ответ HTTP-сценария list_product_types."""

    items: tuple[ProductTypeListItemResponse, ...]
    total: int
    page: int
    page_size: int
