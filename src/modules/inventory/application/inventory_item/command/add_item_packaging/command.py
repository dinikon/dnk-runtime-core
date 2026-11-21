from dataclasses import dataclass
from decimal import Decimal
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)


@dataclass(frozen=True, slots=True)
class AddItemPackagingCommand:
    """Передаёт намерение добавить вариант упаковки существующего товара."""

    inventory_item_id: InventoryItemIdVO
    packaging_type_id: PackagingTypeIdVO
    code: str
    name: str
    content_quantity: Decimal
    content_uom: str
