from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True, frozen=True)
class PriceListIdVO(EntityIdVO):
    """Идентификатор price_list."""


__all__ = ["PriceListIdVO"]
