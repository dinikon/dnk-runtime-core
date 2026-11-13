from dataclasses import dataclass

from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class SetDefaultStorageLocationCommand:
    """Передаёт намерение назначить существующую локацию основной для склада."""

    warehouse_id: WarehouseIdVO
    location_id: StockLocationIdVO
