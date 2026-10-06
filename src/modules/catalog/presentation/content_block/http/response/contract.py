from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)


class BlockResponse(BaseModel):
    """Стабильная OpenAPI-схема для ответов о контент-блоке."""

    id: UUID
    code: str
    type: ContentBlockType
    is_system: bool
    translations: dict[str, str]
