from dataclasses import dataclass

from src.modules.contact_point.domain.contact_point.value_object import (
    ContactPointIdVO,
    ContactPointTypeVO,
)
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListContactPointBindingsQuery:
    tenant_id: EntityIdVO
    contact_point_type: ContactPointTypeVO | None = None
    contact_point_id: ContactPointIdVO | None = None
    owner_object_id: EntityIdVO | None = None
    owner_record_id: EntityIdVO | None = None
    is_active: bool | None = None
    limit: int = 50
    offset: int = 0


__all__ = ["ListContactPointBindingsQuery"]
