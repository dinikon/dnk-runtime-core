from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CompanyResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа с одной компанией."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    legal_name: str


__all__ = ["CompanyResponseSchema"]
