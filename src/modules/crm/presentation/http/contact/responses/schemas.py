from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ContactResponse(BaseModel):
    """HTTP-представление CRM-контакта."""

    id: UUID
    first_name: str
    last_name: str | None
    middle_name: str | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID


class ContactListResponse(BaseModel):
    """Offset-страница CRM-контактов."""

    items: list[ContactResponse]
    total: int
    limit: int
    offset: int


__all__ = ["ContactListResponse", "ContactResponse"]
