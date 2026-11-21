from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)


@dataclass(frozen=True, slots=True)
class GetStockSerialQuery:
    """Ограничивает чтение карточки идентификаторами экземпляра и его владельца."""

    inventory_item_id: InventoryItemIdVO
    serial_id: StockSerialIdVO
