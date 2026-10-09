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


class ReplaceProductTypeSchemaRequest(BaseModel):
    """Тело HTTP-сценария replace_product_type_schema; лишние поля отвергаются."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    expected_schema_version: int = Field(ge=1)
    blocks: list[BlockLinkRequest]
