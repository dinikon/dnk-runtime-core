from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.contact_point.domain.contact_point import ContactPointTypeVO


class OwnerContactPointResponseSchema(BaseModel):
    binding_id: UUID
    contact_point_id: UUID
    contact_point_type: ContactPointTypeVO
    raw_value: str
    normalized_value: str
    is_primary: bool
    created_at: datetime
    updated_at: datetime


class ListOwnerContactPointsResponseSchema(BaseModel):
    items: list[OwnerContactPointResponseSchema]
    count: int


__all__ = [
    "ListOwnerContactPointsResponseSchema",
    "OwnerContactPointResponseSchema",
]
