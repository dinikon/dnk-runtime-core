from dataclasses import dataclass
from typing import Any
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO


@dataclass(slots=True, frozen=True)
class SaveMappingCommand:
    """Входные данные действия save_mapping."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    price_list_id: PriceListIdVO
    source_config: dict[str, Any]
    mapping_config: dict[str, Any]


__all__ = ["SaveMappingCommand"]
