from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from src.modules.contact_points.application.query.list_labels.dto import (
    ListContactPointLabelDTO,
)


class ListLabelResponse(BaseModel):
    """Подпись в списке настроек."""

    id: UUID
    type: Literal["phone", "email"]
    name: str
    is_active: bool

    @classmethod
    def from_dto(cls, dto: ListContactPointLabelDTO) -> "ListLabelResponse":
        return cls(
            id=dto.id.uuid, type=dto.type.value, name=dto.name, is_active=dto.is_active
        )
