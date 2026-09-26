from dataclasses import dataclass
from src.modules.contact_points.domain.binding.value_object.target import (
    ContactPointTargetVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class GetTargetsContactPointsQuery:
    """Пакетное чтение одной или нескольких карточек."""

    tenant_id: EntityIdVO
    targets: tuple[ContactPointTargetVO, ...]


__all__ = ["GetTargetsContactPointsQuery"]
