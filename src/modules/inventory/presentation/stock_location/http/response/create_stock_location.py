from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.application.stock_location.command.create_stock_location.dto import (
    CreateStockLocationResultDTO,
)


class CreateStockLocationResponse(BaseModel):
    """Описывает отдельный HTTP-контракт собственных полей локации."""

    id: UUID
    warehouse_id: UUID
    parent_location_id: UUID | None
    code: str
    name: str
    location_type: LocationType
    is_active: bool

    @classmethod
    def from_dto(cls, dto: CreateStockLocationResultDTO) -> Self:
        """Явно преобразует результат сценария в HTTP-представление."""
        return cls(
            id=dto.id,
            warehouse_id=dto.warehouse_id,
            parent_location_id=dto.parent_location_id,
            code=dto.code,
            name=dto.name,
            location_type=dto.location_type,
            is_active=dto.is_active,
        )
