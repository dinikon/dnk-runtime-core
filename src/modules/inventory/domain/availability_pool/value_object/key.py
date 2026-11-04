from dataclasses import dataclass

from src.modules.inventory.domain.availability_pool.error import (
    InvalidAvailabilityPoolKeyError,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.value_object.stock_owner_id import StockOwnerIdVO
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class AvailabilityPoolKeyVO:
    """Неизменяемая область общего резерва: товар, склад и явный владелец."""

    inventory_item_id: InventoryItemIdVO
    warehouse_id: WarehouseIdVO
    owner_id: StockOwnerIdVO

    def __post_init__(self) -> None:
        """Требует типизированные ссылки без включения локаций, партий и серий в ключ."""
        if (
            not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.warehouse_id, WarehouseIdVO)
            or not isinstance(self.owner_id, StockOwnerIdVO)
        ):
            raise InvalidAvailabilityPoolKeyError(
                "Ключ пула требует типизированные ID товара, склада и владельца."
            )
