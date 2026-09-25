from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from src.modules.crm.presentation.http.contact_points import ContactPointResponse


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
    phones: list[ContactPointResponse] = Field(default_factory=list)
    emails: list[ContactPointResponse] = Field(default_factory=list)


class ContactListResponse(BaseModel):
    """Offset-страница CRM-контактов."""

    items: list[ContactResponse]
    total: int
    limit: int
    offset: int


__all__ = ["ContactListResponse", "ContactResponse"]
