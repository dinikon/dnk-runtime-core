from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ContactListItemResponseSchema(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    first_name: str | None
    last_name: str | None
    middle_name: str | None


class ListContactsResponseSchema(BaseModel):
    items: list[ContactListItemResponseSchema] = Field(default_factory=list)
    total: int
    limit: int
    offset: int
