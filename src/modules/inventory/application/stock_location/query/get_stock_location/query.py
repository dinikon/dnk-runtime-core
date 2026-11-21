from dataclasses import dataclass

from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)


@dataclass(frozen=True, slots=True)
class GetStockLocationQuery:
    """Ограничивает чтение карточки выбранным складом текущего tenant."""

    warehouse_id: WarehouseIdVO
    location_id: StockLocationIdVO
