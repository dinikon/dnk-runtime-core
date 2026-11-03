from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
from src.modules.inventory.domain.stock_position.error import (
    InvalidStockDimensionsError,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.value_object.stock_status import StockStatus


@dataclass(frozen=True, slots=True)
class StockDimensionsVO:
    """Неизменяемый ключ физического запаса без дублирования склада локации."""

    inventory_item_id: InventoryItemIdVO
    location_id: StockLocationIdVO
    owner_id: StockOwnerIdVO
    lot_id: StockLotIdVO | None
    serial_id: StockSerialIdVO | None
    stock_status: StockStatus

    def __post_init__(self) -> None:
        """Проверяет собственные типы ссылок, явного владельца и состояния запаса."""
        if (
            not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.location_id, StockLocationIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
            or (self.lot_id is not None and not isinstance(self.lot_id, StockLotIdVO))
            or (
                self.serial_id is not None
                and not isinstance(self.serial_id, StockSerialIdVO)
            )
            or not isinstance(self.stock_status, StockStatus)
        ):
            raise InvalidStockDimensionsError(
                "Нужны типизированные измерения с явным владельцем запаса."
            )
