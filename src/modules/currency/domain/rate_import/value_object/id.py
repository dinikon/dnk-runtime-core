from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class RateImportIdVO(EntityIdVO):
    """Identity of a rate import record."""


__all__ = ["RateImportIdVO"]
