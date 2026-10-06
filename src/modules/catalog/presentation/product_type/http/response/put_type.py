from uuid import UUID
from src.modules.catalog.application.product_type.command.put_product_type.dto import (
    PutProductTypeResultDTO,
)

from pydantic import BaseModel
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)
from src.modules.catalog.domain.product_type.aggregate import ContentScope


class PutTypeBlockResponse(BaseModel):
    block_id: UUID
    code: str
    type: ContentBlockType
    scope: ContentScope
    required: bool
    position: int
    translations: dict[str, str]


class PutTypeResponse(BaseModel):
    id: UUID
    code: str
    is_system: bool
    schema_version: int
    translations: dict[str, str]
    blocks: list[PutTypeBlockResponse]

    @classmethod
    def from_dto(cls, dto: PutProductTypeResultDTO) -> "PutTypeResponse":
        return cls(
            id=dto.id,
            code=dto.code,
            is_system=dto.is_system,
            schema_version=dto.schema_version,
            translations=dict(dto.translations),
            blocks=[
                PutTypeBlockResponse(
                    block_id=item.block_id,
                    code=item.code,
                    type=item.type,
                    scope=item.scope,
                    required=item.required,
                    position=item.position,
                    translations=dict(item.translations),
                )
                for item in dto.blocks
            ],
        )
