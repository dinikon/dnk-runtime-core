from dataclasses import dataclass

from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)


@dataclass(frozen=True, slots=True)
class CreateStockLocationCommand:
    """Передаёт ручные значения и ссылки без подстановки активности новой локации."""

    warehouse_id: WarehouseIdVO
    code: str
    name: str
    location_type: LocationType
    parent_location_id: StockLocationIdVO | None = None
