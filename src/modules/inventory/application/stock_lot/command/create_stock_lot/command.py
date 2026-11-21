from dataclasses import dataclass
from datetime import date

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)


@dataclass(frozen=True, slots=True)
class CreateStockLotCommand:
    """Передаёт ручной номер и необязательные календарные даты партии выбранного SKU."""

    inventory_item_id: InventoryItemIdVO
    number: str
    manufactured_on: date | None = None
    expires_on: date | None = None
