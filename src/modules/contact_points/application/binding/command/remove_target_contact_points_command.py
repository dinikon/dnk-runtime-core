from dataclasses import dataclass
from src.modules.contact_points.domain.binding.value_object.target import (
    ContactPointTargetVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class RemoveTargetContactPointsCommand:
    """Удаление связей перед удалением владельца."""

    tenant_id: EntityIdVO
    target: ContactPointTargetVO


__all__ = ["RemoveTargetContactPointsCommand"]
