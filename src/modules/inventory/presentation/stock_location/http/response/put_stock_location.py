from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.stock_location.command.update_stock_location.dto import (
    UpdateStockLocationResultDTO,
)
from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)


class PutStockLocationResponse(BaseModel):
    """Описывает отдельный HTTP-контракт результата PUT локации."""

    id: UUID
    warehouse_id: UUID
    parent_location_id: UUID | None
    code: str
    name: str
    location_type: LocationType
    is_active: bool

    @classmethod
    def from_dto(cls, dto: UpdateStockLocationResultDTO) -> Self:
        """Явно преобразует все собственные поля результата сценария."""
        return cls(
            id=dto.id,
            warehouse_id=dto.warehouse_id,
            parent_location_id=dto.parent_location_id,
            code=dto.code,
            name=dto.name,
            location_type=dto.location_type,
            is_active=dto.is_active,
        )
