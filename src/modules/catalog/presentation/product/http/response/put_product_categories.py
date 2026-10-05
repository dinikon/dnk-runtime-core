from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.product.command.put_product_categories.dto import (
    PutProductCategoriesResultDTO,
)


class PutProductCategoriesResponse(BaseModel):
    product_id: UUID
    category_ids: list[UUID]
    primary_category_id: UUID | None
    updated_at: datetime
    updated_by: UUID

    @classmethod
    def from_dto(
        cls, dto: PutProductCategoriesResultDTO
    ) -> "PutProductCategoriesResponse":
        return cls(
            product_id=dto.product_id,
            category_ids=list(dto.category_ids),
            primary_category_id=dto.primary_category_id,
            updated_at=dto.updated_at,
            updated_by=dto.updated_by,
        )
