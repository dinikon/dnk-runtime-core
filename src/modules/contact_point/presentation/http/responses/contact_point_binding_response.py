from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.contact_point.domain.contact_point import ContactPointTypeVO


class ContactPointBindingResponseSchema(BaseModel):
    id: UUID
    contact_point_id: UUID
    contact_point_type: ContactPointTypeVO
    owner_object_id: UUID
    owner_record_id: UUID
    is_primary: bool
    is_active: bool
    detached_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ListContactPointBindingsResponseSchema(BaseModel):
    items: list[ContactPointBindingResponseSchema]
    count: int
    limit: int
    offset: int


__all__ = [
    "ContactPointBindingResponseSchema",
    "ListContactPointBindingsResponseSchema",
]
