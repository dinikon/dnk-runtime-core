from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.attribute.command.create_attribute.dto import (
    CreateAttributeResultDTO,
)


class CreatedAttributeOptionResponse(BaseModel):
    id: UUID
    code: str


class CreateAttributeResponse(BaseModel):
    id: UUID
    code: str
    options: list[CreatedAttributeOptionResponse]
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: CreateAttributeResultDTO) -> "CreateAttributeResponse":
        return cls(
            id=dto.id,
            code=dto.code,
            options=[
                CreatedAttributeOptionResponse(id=item.id, code=item.code)
                for item in dto.options
            ],
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            created_by=dto.created_by,
            updated_by=dto.updated_by,
        )
