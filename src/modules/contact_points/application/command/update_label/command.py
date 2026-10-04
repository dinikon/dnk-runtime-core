from dataclasses import dataclass
from src.modules.contact_points.domain.value_object.label_identifier import (
    ContactPointLabelIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class UpdateContactPointLabelCommand:
    """Команда update подписи текущего tenant."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    label_id: ContactPointLabelIdVO
    name: str | None = None
    is_active: bool | None = None


__all__ = ["UpdateContactPointLabelCommand"]
