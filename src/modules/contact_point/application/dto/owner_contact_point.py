from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.contact_point.domain.contact_point.value_object import (
    ContactPointTypeVO,
)


@dataclass(frozen=True, slots=True)
class OwnerContactPointDTO:
    binding_id: UUID
    contact_point_id: UUID
    contact_point_type: ContactPointTypeVO
    raw_value: str
    normalized_value: str
    is_primary: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class OwnerContactPointListDTO:
    items: tuple[OwnerContactPointDTO, ...]
    count: int


__all__ = [
    "OwnerContactPointDTO",
    "OwnerContactPointListDTO",
]
