from uuid import UUID

from pydantic import BaseModel


class UpdateContactRequestSchema(BaseModel):
    contact_id: UUID
    first_name: str
    last_name: str | None = None
    middle_name: str | None = None
