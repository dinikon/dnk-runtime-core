from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)


@dataclass(frozen=True, slots=True)
class GetInventoryItemQuery:
    """Запрашивает карточку складской позиции в текущем tenant."""

    inventory_item_id: InventoryItemIdVO
