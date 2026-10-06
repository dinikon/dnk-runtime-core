from uuid import UUID
from pydantic import BaseModel

from src.modules.catalog.application.product.query.get_variant.dto import (
    GetVariantResultDTO,
)


class GetVariantResponse(BaseModel):
    id: UUID
    product_id: UUID
    sku_id: UUID
    sku_code: str
    requested_locale: str
    content_locales: list[str]
    short_description: str | None

    @classmethod
    def from_dto(cls, dto: GetVariantResultDTO) -> "GetVariantResponse":
        return cls(
            id=dto.id,
            product_id=dto.product_id,
            sku_id=dto.sku_id,
            sku_code=dto.sku_code,
            requested_locale=dto.requested_locale,
            content_locales=list(dto.content_locales),
            short_description=dto.short_description,
        )
