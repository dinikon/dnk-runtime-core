from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UpdateContactResponseSchema(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    first_name: str | None
    last_name: str | None
    middle_name: str | None
