from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ResolutionFailureIdVO(EntityIdVO):
    """Identity of a resolution failure record."""


__all__ = ["ResolutionFailureIdVO"]
