from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_serial.error import (
    InvalidStockSerialSnapshotError,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)


@dataclass(frozen=True, slots=True)
class StockSerialSnapshot:
    """Неизменяемые идентичность, товар и принадлежность партии без количества и дат."""

    id: StockSerialIdVO
    inventory_item_id: InventoryItemIdVO
    lot_id: StockLotIdVO | None

    def ensure_valid(self) -> None:
        """Проверяет собственные типы ссылок снимка экземпляра."""
        if (
            not isinstance(self.id, StockSerialIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or (self.lot_id is not None and not isinstance(self.lot_id, StockLotIdVO))
        ):
            raise InvalidStockSerialSnapshotError(
                "Нужен типизированный снимок серийного экземпляра."
            )
