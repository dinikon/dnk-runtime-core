from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ProviderRateIdVO(EntityIdVO):
    """Identity of a provider rate record."""


__all__ = ["ProviderRateIdVO"]
