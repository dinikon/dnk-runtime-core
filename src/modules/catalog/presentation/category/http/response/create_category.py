from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.category.command.create_category.dto import (
    CreateCategoryResultDTO,
)


class CreateCategoryResponse(BaseModel):
    id: UUID
    parent_id: UUID | None
    locales: list[str]
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: CreateCategoryResultDTO) -> "CreateCategoryResponse":
        return cls(
            id=dto.id,
            parent_id=dto.parent_id,
            locales=list(dto.locales),
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            created_by=dto.created_by,
            updated_by=dto.updated_by,
        )
