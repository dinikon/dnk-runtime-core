from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.crm.application.contact.command.create_contact.dto import (
    CreateContactResultDTO,
)


class CreateContactResponse(BaseModel):
    """HTTP-представление созданного контакта без связанных сущностей."""

    id: UUID
    first_name: str
    last_name: str
    middle_name: str | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: CreateContactResultDTO) -> "CreateContactResponse":
        """Явно переносит результат сценария в HTTP-ответ."""
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
