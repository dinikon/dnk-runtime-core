from dataclasses import dataclass

from src.modules.contact_point.domain.contact_point.value_object import (
    ContactPointIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class GetContactPointQuery:
    tenant_id: EntityIdVO
    contact_point_id: ContactPointIdVO


__all__ = ["GetContactPointQuery"]
