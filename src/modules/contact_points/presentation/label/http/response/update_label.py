from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from src.modules.contact_points.application.label.command.update_label.dto import (
    UpdateContactPointLabelDTO,
)


class UpdateLabelResponse(BaseModel):
    """Изменённая подпись."""

    id: UUID
    type: Literal["phone", "email"]
    name: str
    is_active: bool

    @classmethod
    def from_dto(cls, dto: UpdateContactPointLabelDTO) -> "UpdateLabelResponse":
        return cls(
            id=dto.id.uuid, type=dto.type.value, name=dto.name, is_active=dto.is_active
        )
