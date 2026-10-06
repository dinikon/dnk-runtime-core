from uuid import UUID
from pydantic import BaseModel

from src.modules.catalog.application.product.command.put_variant_content.dto import (
    PutVariantContentResultDTO,
)


class PutVariantContentResponse(BaseModel):
    variant_id: UUID
    locale: str
    short_description: str

    @classmethod
    def from_dto(cls, dto: PutVariantContentResultDTO) -> "PutVariantContentResponse":
        return cls(
            variant_id=dto.variant_id,
            locale=dto.locale,
            short_description=dto.short_description,
        )
