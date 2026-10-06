from uuid import UUID
from src.modules.catalog.application.product_type.query.list_product_types.dto import (
    ProductTypeListItemDTO,
)

from pydantic import BaseModel
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)
from src.modules.catalog.domain.product_type.aggregate import ContentScope


class ListTypeBlockResponse(BaseModel):
    block_id: UUID
    code: str
    type: ContentBlockType
    scope: ContentScope
    required: bool
    position: int
    translations: dict[str, str]


class ListTypeResponse(BaseModel):
    id: UUID
    code: str
    is_system: bool
    schema_version: int
    translations: dict[str, str]
    blocks: list[ListTypeBlockResponse]

    @classmethod
    def from_dto(cls, dto: ProductTypeListItemDTO) -> "ListTypeResponse":
        return cls(
            id=dto.id,
            code=dto.code,
            is_system=dto.is_system,
            schema_version=dto.schema_version,
            translations=dict(dto.translations),
            blocks=[
                ListTypeBlockResponse(
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
