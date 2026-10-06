from uuid import UUID
from src.modules.catalog.application.content_block.query.list_content_blocks.dto import (
    ContentBlockListItemDTO,
)

from pydantic import BaseModel
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)


class ListBlockResponse(BaseModel):
    id: UUID
    code: str
    type: ContentBlockType
    is_system: bool
    translations: dict[str, str]

    @classmethod
    def from_dto(cls, dto: ContentBlockListItemDTO) -> "ListBlockResponse":
        return cls(
            id=dto.id,
            code=dto.code,
            type=dto.type,
            is_system=dto.is_system,
            translations=dict(dto.translations),
        )
