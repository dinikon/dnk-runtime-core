from uuid import UUID
from pydantic import BaseModel

from src.modules.catalog.application.product.command.put_variant_structure.dto import (
    PutVariantStructureResultDTO,
)
from src.modules.catalog.domain.product.value_object.kind import ProductKind


class PutVariantStructureResponse(BaseModel):
    product_id: UUID
    kind: ProductKind
    variant_ids: list[UUID]

    @classmethod
    def from_dto(
        cls, dto: PutVariantStructureResultDTO
    ) -> "PutVariantStructureResponse":
        return cls(
            product_id=dto.product_id, kind=dto.kind, variant_ids=list(dto.variant_ids)
        )
