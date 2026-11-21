from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)


@dataclass(frozen=True, slots=True)
class DeleteInventoryItemCommand:
    """Передаёт идентификатор удаляемой позиции."""

    inventory_item_id: InventoryItemIdVO
