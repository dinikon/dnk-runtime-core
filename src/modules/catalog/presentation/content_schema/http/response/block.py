from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.content_schema.contracts import BlockDefinitionDTO
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)


class BlockResponse(BaseModel):
    id: UUID
    code: str
    type: ContentBlockType
    is_system: bool
    translations: dict[str, str]

    @classmethod
    def from_dto(cls, dto: BlockDefinitionDTO) -> "BlockResponse":
        return cls(
            id=dto.id,
            code=dto.code,
            type=dto.type,
            is_system=dto.is_system,
            translations=dto.translations,
        )
