from uuid import UUID

from pydantic import BaseModel


class GetContactRequestSchema(BaseModel):
    contact_id: UUID
