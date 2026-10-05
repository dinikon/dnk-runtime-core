from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.attribute.query.list_attributes.dto import (
    AttributeDetailsDTO,
)


class AttributeOptionResponse(BaseModel):
    id: UUID
    code: str
    name: str | None


class GetAttributeResponse(BaseModel):
    id: UUID
    code: str
    type: str
    name: str | None
    options: list[AttributeOptionResponse]

    @classmethod
    def from_dto(cls, dto: AttributeDetailsDTO) -> "GetAttributeResponse":
        return cls(
            id=dto.id,
            code=dto.code,
            type=dto.type,
            name=dto.name,
            options=[
                AttributeOptionResponse(id=item.id, code=item.code, name=item.name)
                for item in dto.options
            ],
        )
