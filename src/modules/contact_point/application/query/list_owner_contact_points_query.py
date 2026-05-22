from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListOwnerContactPointsQuery:
    tenant_id: EntityIdVO
    owner_object_id: EntityIdVO
    owner_record_id: EntityIdVO


__all__ = ["ListOwnerContactPointsQuery"]
