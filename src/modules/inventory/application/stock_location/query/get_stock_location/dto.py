from dataclasses import dataclass
from uuid import UUID

from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)


@dataclass(frozen=True, slots=True)
class GetStockLocationResultDTO:
    """Передаёт собственные поля карточки локации."""

    id: UUID
    warehouse_id: UUID
    parent_location_id: UUID | None
    code: str
    name: str
    location_type: LocationType
    is_active: bool
