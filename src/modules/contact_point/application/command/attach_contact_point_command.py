from dataclasses import dataclass

from src.modules.contact_point.domain.contact_point.value_object import (
    ContactPointTypeVO,
)
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class AttachContactPointCommand:
    tenant_id: EntityIdVO
    owner_object_id: EntityIdVO
    owner_record_id: EntityIdVO
    contact_point_type: ContactPointTypeVO
    raw_value: str
    is_primary: bool = False


__all__ = ["AttachContactPointCommand"]
