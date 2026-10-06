from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.content_schema.contracts import (
    ProductTypeSchemaDTO,
)
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)
from src.modules.catalog.domain.product_type.aggregate import ContentScope


class TypeBlockResponse(BaseModel):
    block_id: UUID
    code: str
    type: ContentBlockType
    scope: ContentScope
    required: bool
    position: int
    translations: dict[str, str]


class ProductTypeResponse(BaseModel):
    id: UUID
    code: str
    is_system: bool
    schema_version: int
    translations: dict[str, str]
    blocks: list[TypeBlockResponse]

    @classmethod
    def from_dto(cls, dto: ProductTypeSchemaDTO) -> "ProductTypeResponse":
        return cls(
            id=dto.id,
            code=dto.code,
            is_system=dto.is_system,
            schema_version=dto.schema_version,
            translations=dto.translations,
            blocks=[
                TypeBlockResponse(
                    block_id=item.block_id,
                    code=item.code,
                    type=item.type,
                    scope=item.scope,
                    required=item.required,
                    position=item.position,
                    translations=item.translations,
                )
                for item in dto.blocks
            ],
        )
