from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.contact_point.domain.contact_point.value_object import (
    ContactPointTypeVO,
)


@dataclass(frozen=True, slots=True)
class ContactPointDTO:
    id: UUID
    created_at: datetime
    updated_at: datetime
    contact_point_type: ContactPointTypeVO
    raw_value: str
    normalized_value: str


@dataclass(frozen=True, slots=True)
class ContactPointListDTO:
    items: tuple[ContactPointDTO, ...]
    count: int
    limit: int
    offset: int


__all__ = [
    "ContactPointDTO",
    "ContactPointListDTO",
]
