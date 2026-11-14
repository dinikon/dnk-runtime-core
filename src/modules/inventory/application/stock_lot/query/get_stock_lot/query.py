from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO


@dataclass(frozen=True, slots=True)
class GetStockLotQuery:
    """Ограничивает чтение карточки идентификаторами партии и её владельца."""

    inventory_item_id: InventoryItemIdVO
    lot_id: StockLotIdVO
