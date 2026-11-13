from dataclasses import dataclass
from uuid import UUID

from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)


@dataclass(frozen=True, slots=True)
class StockLocationListItemDTO:
    """Описывает строку плоского списка без дочерних адресов и остатков."""

    id: UUID
    warehouse_id: UUID
    parent_location_id: UUID | None
    code: str
    name: str
    location_type: LocationType
    is_active: bool


@dataclass(frozen=True, slots=True)
class ListStockLocationsResultDTO:
    """Передаёт страницу и total по тому же набору фильтров."""

    items: tuple[StockLocationListItemDTO, ...]
    total: int
    offset: int
    limit: int
