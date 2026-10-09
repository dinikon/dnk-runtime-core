from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from src.modules.catalog.domain.product_type.value_object.block_link import ContentScope


class BlockLinkRequest(BaseModel):
    """HTTP-значение связи блока, не универсальный запрос изменения."""

    model_config = ConfigDict(extra="forbid")
    block_id: UUID
    scope: ContentScope
    required: bool
    position: int = Field(ge=0)


class CreateProductTypeRequest(BaseModel):
    """Тело HTTP-сценария create_product_type; лишние поля отвергаются."""

    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=64)
    locale: str = Field(min_length=2, max_length=64)
    label: str = Field(min_length=1, max_length=255)
    blocks: list[BlockLinkRequest]
