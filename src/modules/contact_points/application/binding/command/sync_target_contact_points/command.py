from dataclasses import dataclass
from src.modules.contact_points.domain.binding.value_object.target import (
    ContactPointTargetVO,
)
from src.modules.contact_points.domain.binding.value_object.draft import (
    ContactPointDraftVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class SyncTargetContactPointsCommand:
    """Полные переданные списки; None сохраняет текущий список."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    target: ContactPointTargetVO
    phones: tuple[ContactPointDraftVO, ...] | None = None
    emails: tuple[ContactPointDraftVO, ...] | None = None


__all__ = ["SyncTargetContactPointsCommand"]
