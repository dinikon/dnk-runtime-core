from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.crm.application.contact.command.update_contact.dto import (
    UpdateContactResultDTO,
)


class PatchContactResponse(BaseModel):
    """Результат частичного изменения ФИО."""

    id: UUID
    first_name: str
    last_name: str | None
    middle_name: str | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: UpdateContactResultDTO) -> "PatchContactResponse":
        return cls(
            id=dto.id,
            first_name=dto.first_name,
            last_name=dto.last_name,
            middle_name=dto.middle_name,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            created_by=dto.created_by,
            updated_by=dto.updated_by,
        )
