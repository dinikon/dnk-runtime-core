from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.product.query.get_product.dto import (
    ProductContentDTO,
    ProductDetailsDTO,
)


class GetProductContentResponse(BaseModel):
    locale: str
    name: str
    description: str | None

    @classmethod
    def from_dto(cls, dto: ProductContentDTO) -> "GetProductContentResponse":
        return cls(
            locale=dto.locale,
            name=dto.name,
            description=dto.description,
        )


class GetProductResponse(BaseModel):
    id: UUID
    type: str
    variant_id: UUID
    sku_id: UUID
    sku_code: str
    requested_locale: str
    content_locales: list[str]
    content: GetProductContentResponse | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: ProductDetailsDTO) -> "GetProductResponse":
        if dto.sku_code is None:
            raise ValueError("GetProductHandler must resolve the SKU code.")
        return cls(
            id=dto.id,
            type=dto.type,
            variant_id=dto.variant_id,
            sku_id=dto.sku_id,
            sku_code=dto.sku_code,
            requested_locale=dto.requested_locale,
            content_locales=list(dto.content_locales),
            content=(
                GetProductContentResponse.from_dto(dto.content)
                if dto.content is not None
                else None
            ),
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            created_by=dto.created_by,
            updated_by=dto.updated_by,
        )
