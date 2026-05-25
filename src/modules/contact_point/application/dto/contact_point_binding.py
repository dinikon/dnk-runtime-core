from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.contact_point.domain.contact_point.value_object import (
    ContactPointTypeVO,
)


@dataclass(frozen=True, slots=True)
class ContactPointBindingDTO:
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


@dataclass(frozen=True, slots=True)
class ContactPointBindingListDTO:
    items: tuple[ContactPointBindingDTO, ...]
    count: int
    limit: int
    offset: int


__all__ = [
    "ContactPointBindingDTO",
    "ContactPointBindingListDTO",
]
