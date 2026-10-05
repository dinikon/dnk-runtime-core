from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.product.command.create_variable_product.dto import (
    CreateVariableProductResultDTO,
)


class CreatedVariableSelectionResponse(BaseModel):
    attribute_id: UUID
    option_id: UUID


class CreatedVariableVariantResponse(BaseModel):
    id: UUID
    sku_id: UUID
    sku_code: str
    selections: list[CreatedVariableSelectionResponse]


class CreateVariableProductResponse(BaseModel):
    id: UUID
    type: str
    variants: list[CreatedVariableVariantResponse]
    content_locales: list[str]
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    @classmethod
    def from_dto(
        cls, dto: CreateVariableProductResultDTO
    ) -> "CreateVariableProductResponse":
        return cls(
            id=dto.id,
            type=dto.type,
            variants=[
                CreatedVariableVariantResponse(
                    id=item.id,
                    sku_id=item.sku_id,
                    sku_code=item.sku_code,
                    selections=[
                        CreatedVariableSelectionResponse(
                            attribute_id=selection.attribute_id,
                            option_id=selection.option_id,
                        )
                        for selection in item.selections
                    ],
                )
                for item in dto.variants
            ],
            content_locales=list(dto.content_locales),
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            created_by=dto.created_by,
            updated_by=dto.updated_by,
        )
