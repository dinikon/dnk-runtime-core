from uuid import UUID
from pydantic import BaseModel

from src.modules.catalog.application.product.command.create_variable_product.dto import (
    CreateVariableProductResultDTO,
)


class CreateVariableProductResponse(BaseModel):
    id: UUID
    variant_ids: list[UUID]
    product_type_id: UUID
    schema_version: int

    @classmethod
    def from_dto(
        cls, dto: CreateVariableProductResultDTO
    ) -> "CreateVariableProductResponse":
        return cls(
            id=dto.id,
            variant_ids=list(dto.variant_ids),
            product_type_id=dto.product_type_id,
            schema_version=dto.schema_version,
        )
