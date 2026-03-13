from uuid import UUID

from pydantic import BaseModel


class DeleteContactRequestSchema(BaseModel):
    contact_id: UUID
