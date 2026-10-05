from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.category.command.put_category_content.dto import (
    PutCategoryContentResultDTO,
)


class PutCategoryContentResponse(BaseModel):
    category_id: UUID
    locale: str
    name: str
    updated_at: datetime
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: PutCategoryContentResultDTO) -> "PutCategoryContentResponse":
        return cls(
            category_id=dto.category_id,
            locale=dto.locale,
            name=dto.name,
            updated_at=dto.updated_at,
            updated_by=dto.updated_by,
        )
