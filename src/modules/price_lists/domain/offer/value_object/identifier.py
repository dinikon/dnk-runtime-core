from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class OfferIdVO(EntityIdVO):
    """Идентификатор offer."""


@dataclass(slots=True, frozen=True)
class OfferStateIdVO(EntityIdVO):
    """Идентификатор offer."""


__all__ = ["OfferIdVO", "OfferStateIdVO"]
