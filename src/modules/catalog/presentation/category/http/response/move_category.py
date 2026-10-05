from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.category.command.move_category.dto import (
    MoveCategoryResultDTO,
)


class MoveCategoryResponse(BaseModel):
    id: UUID
    parent_id: UUID | None
    updated_at: datetime
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: MoveCategoryResultDTO) -> "MoveCategoryResponse":
        return cls(
            id=dto.id,
            parent_id=dto.parent_id,
            updated_at=dto.updated_at,
            updated_by=dto.updated_by,
        )
