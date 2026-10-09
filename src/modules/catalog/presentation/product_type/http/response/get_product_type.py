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


class GetProductTypeResponse(BaseModel):
    """Ответ HTTP-сценария get_product_type."""

    id: UUID
    code: str
    is_system: bool
    revision: int
    label: str | None
    locales: tuple[str, ...]
    schema_version: int
    blocks: tuple[SchemaBlockResponse, ...]
