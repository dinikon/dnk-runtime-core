from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO


@dataclass(frozen=True, slots=True)
class CreateStockSerialCommand:
    """Передаёт номер экземпляра и необязательную партию выбранного SKU без дат."""

    inventory_item_id: InventoryItemIdVO
    number: str
    lot_id: StockLotIdVO | None = None
