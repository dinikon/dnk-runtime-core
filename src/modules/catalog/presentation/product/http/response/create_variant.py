from uuid import UUID
from pydantic import BaseModel

from src.modules.catalog.application.product.command.create_variant.dto import (
    CreateVariantResultDTO,
)


class CreateVariantResponse(BaseModel):
    id: UUID
    product_id: UUID
    sku_id: UUID
    sku_code: str

    @classmethod
    def from_dto(cls, dto: CreateVariantResultDTO) -> "CreateVariantResponse":
        return cls(
            id=dto.id,
            product_id=dto.product_id,
            sku_id=dto.sku_id,
            sku_code=dto.sku_code,
        )
