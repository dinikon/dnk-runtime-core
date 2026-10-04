from dataclasses import dataclass
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class ResolveContactPointTargetsQuery:
    """Обратный поиск владельцев нормализованного адреса."""

    tenant_id: EntityIdVO
    type: ContactPointType
    value: str
    country_code: str | None = None


__all__ = ["ResolveContactPointTargetsQuery"]
