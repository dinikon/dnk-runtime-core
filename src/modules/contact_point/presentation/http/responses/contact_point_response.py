from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.contact_point.domain.contact_point import ContactPointTypeVO


class ContactPointResponseSchema(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    contact_point_type: ContactPointTypeVO
    raw_value: str
    normalized_value: str


class ListContactPointsResponseSchema(BaseModel):
    items: list[ContactPointResponseSchema]
    count: int
    limit: int
    offset: int


__all__ = [
    "ContactPointResponseSchema",
    "ListContactPointsResponseSchema",
]
