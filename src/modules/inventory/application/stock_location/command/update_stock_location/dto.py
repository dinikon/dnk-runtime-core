from dataclasses import dataclass
from uuid import UUID

from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)


@dataclass(frozen=True, slots=True)
class UpdateStockLocationResultDTO:
    """Передаёт полную карточку после изменения с прежними ID, родителем и типом."""

    id: UUID
    warehouse_id: UUID
    parent_location_id: UUID | None
    code: str
    name: str
    location_type: LocationType
    is_active: bool
