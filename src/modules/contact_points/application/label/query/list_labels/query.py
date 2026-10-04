from dataclasses import dataclass
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class ListContactPointLabelsQuery:
    """Чтение активных и архивных подписей своего tenant."""

    tenant_id: EntityIdVO
    type: ContactPointType | None = None


__all__ = ["ListContactPointLabelsQuery"]
