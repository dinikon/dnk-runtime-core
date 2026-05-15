from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListObjectRelationsQuery:
    """Query списка relations, связанных с object."""

    tenant_id: EntityIdVO
    object_id: RuntimeObjectIdVO


__all__ = ["ListObjectRelationsQuery"]
