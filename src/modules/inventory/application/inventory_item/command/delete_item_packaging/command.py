from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.item_packaging_id import (
    ItemPackagingIdVO,
)


@dataclass(frozen=True, slots=True)
class DeleteItemPackagingCommand:
    """Передаёт идентификаторы товара и удаляемой собственной упаковки."""

    inventory_item_id: InventoryItemIdVO
    packaging_id: ItemPackagingIdVO
