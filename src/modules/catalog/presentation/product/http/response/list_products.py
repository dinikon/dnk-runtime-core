from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from src.modules.catalog.application.product.query.list_products.dto import (
    ProductListItemDTO,
)
from src.modules.catalog.domain.product.value_object.kind import ProductKind


class ListProductItemResponse(BaseModel):
    id: UUID
    kind: ProductKind
    name: str | None
    variant_count: int
    primary_category_id: UUID | None
    primary_category_name: str | None
    updated_at: datetime

    @classmethod
    def from_dto(cls, dto: ProductListItemDTO) -> "ListProductItemResponse":
        return cls(
            id=dto.id,
            kind=dto.kind,
            name=dto.name,
            variant_count=dto.variant_count,
            primary_category_id=dto.primary_category_id,
            primary_category_name=dto.primary_category_name,
            updated_at=dto.updated_at,
        )
