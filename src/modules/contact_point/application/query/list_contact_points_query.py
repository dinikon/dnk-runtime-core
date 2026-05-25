from dataclasses import dataclass

from src.modules.contact_point.domain.contact_point.value_object import (
    ContactPointTypeVO,
)
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListContactPointsQuery:
    tenant_id: EntityIdVO
    contact_point_type: ContactPointTypeVO | None = None
    limit: int = 50
    offset: int = 0


__all__ = ["ListContactPointsQuery"]
