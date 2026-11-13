from dataclasses import dataclass

from src.modules.inventory.domain.stock_location.value_object.identifier import (
    StockLocationIdVO,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class UpdateStockLocationCommand:
    """Передаёт принадлежность адреса и явно изменяемые поля без defaults создания."""

    warehouse_id: WarehouseIdVO
    location_id: StockLocationIdVO
    fields: frozenset[str]
    code: str | None = None
    name: str | None = None
    is_active: bool | None = None
