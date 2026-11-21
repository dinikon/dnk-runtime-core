from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO


@dataclass(frozen=True, slots=True)
class UpdateStockSerialCommand:
    """Передаёт явно изменяемые поля, отличая пропуск партии от её очищения."""

    inventory_item_id: InventoryItemIdVO
    serial_id: StockSerialIdVO
    fields: frozenset[str]
    number: str = ""
    lot_id: StockLotIdVO | None = None
