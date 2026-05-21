from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListObjectFeaturesQuery:
    """Query списка feature configs runtime-объекта."""

    tenant_id: EntityIdVO
    object_id: RuntimeObjectIdVO


__all__ = ["ListObjectFeaturesQuery"]
