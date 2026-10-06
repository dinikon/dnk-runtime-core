from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.domain.product.value_object.kind import ProductKind
from src.modules.catalog.application.product.command.create_product.dto import (
    CreateProductResultDTO,
)


class CreateProductResponse(BaseModel):
    id: UUID
    kind: ProductKind
    variant_id: UUID
    sku_id: UUID
    sku_code: str
    content_locales: list[str]
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: CreateProductResultDTO) -> "CreateProductResponse":
        return cls(
            id=dto.id,
            kind=dto.kind,
            variant_id=dto.variant_id,
            sku_id=dto.sku_id,
            sku_code=dto.sku_code,
            content_locales=list(dto.content_locales),
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            created_by=dto.created_by,
            updated_by=dto.updated_by,
        )
