from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)


class ListStockLocationsRequest(BaseModel):
    """Проверяет параметры HTTP-списка, сохраняя явный false и необязательные фильтры."""

    model_config = ConfigDict(extra="forbid")
    offset: int = Field(default=0, ge=0, le=2_147_483_647)
    limit: int = Field(default=50, ge=1, le=100)
    search: str | None = None
    is_active: bool | None = None
    location_type: LocationType | None = None
    parent_location_id: UUID | None = None
