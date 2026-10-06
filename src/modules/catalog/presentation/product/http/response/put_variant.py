from uuid import UUID
from pydantic import BaseModel

from src.modules.catalog.application.product.command.put_variant.dto import (
    PutVariantResultDTO,
)


class PutVariantResponse(BaseModel):
    id: UUID
    product_id: UUID
    sku_id: UUID
    sku_code: str

    @classmethod
    def from_dto(cls, dto: PutVariantResultDTO) -> "PutVariantResponse":
        return cls(
            id=dto.id,
            product_id=dto.product_id,
            sku_id=dto.sku_id,
            sku_code=dto.sku_code,
        )
