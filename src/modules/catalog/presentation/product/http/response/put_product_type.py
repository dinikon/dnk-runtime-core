from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.product.command.put_product_type.dto import (
    PutProductTypeResultDTO,
)


class PutProductTypeResponse(BaseModel):
    product_id: UUID
    product_type_id: UUID
    schema_version: int

    @classmethod
    def from_dto(cls, dto: PutProductTypeResultDTO) -> "PutProductTypeResponse":
        return cls(
            product_id=dto.product_id,
            product_type_id=dto.product_type_id,
            schema_version=dto.schema_version,
        )
