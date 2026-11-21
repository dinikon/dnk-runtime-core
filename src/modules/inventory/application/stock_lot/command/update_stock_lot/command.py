from dataclasses import dataclass
from datetime import date

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO


@dataclass(frozen=True, slots=True)
class UpdateStockLotCommand:
    """Передаёт явно изменяемые даты партии, отличая пропуск поля от очищения."""

    inventory_item_id: InventoryItemIdVO
    lot_id: StockLotIdVO
    fields: frozenset[str]
    manufactured_on: date | None = None
    expires_on: date | None = None
