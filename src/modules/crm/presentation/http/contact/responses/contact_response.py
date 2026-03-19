from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ContactResponseSchema(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_name: str
    first_name: str | None
    middle_name: str | None


__all__ = ["ContactResponseSchema"]
