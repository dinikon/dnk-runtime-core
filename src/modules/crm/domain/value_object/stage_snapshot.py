from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class StageSnapshot:
    """Снимок назначения из внешнего контекста для истории CRM."""

    funnel_id: EntityIdVO
    stage_id: EntityIdVO
    funnel_name: str
    stage_name: str
    kind: str
