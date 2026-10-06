from uuid import UUID
from pydantic import BaseModel

from src.modules.catalog.application.product.command.put_variant_content.dto import (
    PutVariantContentResultDTO,
)


class PutVariantContentResponse(BaseModel):
    variant_id: UUID
    locale: str
    schema_version: int
    blocks: dict[str, str]

    @classmethod
    def from_dto(cls, dto: PutVariantContentResultDTO) -> "PutVariantContentResponse":
        return cls(
            variant_id=dto.variant_id,
            locale=dto.locale,
            schema_version=dto.schema_version,
            blocks=dto.blocks,
        )
