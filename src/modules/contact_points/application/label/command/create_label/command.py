from dataclasses import dataclass
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.contact_points.domain.label.value_object.identifier import (
    ContactPointLabelIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class CreateContactPointLabelCommand:
    """Команда create подписи текущего tenant."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    label_id: ContactPointLabelIdVO
    type: ContactPointType
    name: str


__all__ = ["CreateContactPointLabelCommand"]
