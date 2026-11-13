from dataclasses import dataclass

from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)


@dataclass(frozen=True, slots=True)
class ListStockLocationsQuery:
    """Задаёт плоскую страницу адресов склада с необязательными фильтрами."""

    warehouse_id: WarehouseIdVO
    offset: int = 0
    limit: int = 50
    search: str | None = None
    is_active: bool | None = None
    location_type: LocationType | None = None
    parent_location_id: StockLocationIdVO | None = None
