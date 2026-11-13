from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictStr

from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)


class CreateStockLocationRequest(BaseModel):
    """Принимает ручные данные и необязательного родителя без ID, склада и активности."""

    model_config = ConfigDict(extra="forbid")
    code: StrictStr
    name: StrictStr
    location_type: LocationType
    parent_location_id: UUID | None = None
