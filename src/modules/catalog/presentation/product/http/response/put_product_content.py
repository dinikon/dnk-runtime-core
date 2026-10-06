from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.product.command.put_product_content.dto import (
    PutProductContentResultDTO,
)


class PutProductContentResponse(BaseModel):
    product_id: UUID
    locale: str
    schema_version: int
    blocks: dict[str, str]
    updated_at: datetime
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: PutProductContentResultDTO) -> "PutProductContentResponse":
        return cls(
            product_id=dto.product_id,
            locale=dto.locale,
            schema_version=dto.schema_version,
            blocks=dto.blocks,
            updated_at=dto.updated_at,
            updated_by=dto.updated_by,
        )
