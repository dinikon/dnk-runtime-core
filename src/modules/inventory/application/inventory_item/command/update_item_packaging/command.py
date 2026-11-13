from dataclasses import dataclass
from decimal import Decimal
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.inventory_item.value_object.item_packaging_id import (
    ItemPackagingIdVO,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)


@dataclass(frozen=True, slots=True)
class UpdateItemPackagingCommand:
    """Передаёт идентификаторы и явно заданные изменения собственного варианта упаковки."""

    inventory_item_id: InventoryItemIdVO
    packaging_id: ItemPackagingIdVO
    fields: frozenset[str]
    packaging_type_id: PackagingTypeIdVO | None = None
    code: str | None = None
    name: str | None = None
    content_quantity: Decimal | None = None
    content_uom: str | None = None
