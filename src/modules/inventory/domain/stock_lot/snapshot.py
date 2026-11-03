from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO


@dataclass(frozen=True, slots=True)
class StockLotSnapshot:
    """Неизменяемая идентичность и даты партии для правил серийного экземпляра."""

    id: StockLotIdVO
    inventory_item_id: InventoryItemIdVO
    dates: StockDatesVO
