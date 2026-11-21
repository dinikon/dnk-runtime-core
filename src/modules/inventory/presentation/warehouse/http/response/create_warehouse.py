from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.warehouse.command.create_warehouse.dto import (
    CreateWarehouseResultDTO,
)


class CreateWarehouseResponse(BaseModel):
    """Описывает отдельный HTTP-контракт результата склада."""

    id: UUID
    code: str
    name: str
    is_active: bool
    default_storage_location_id: UUID

    @classmethod
    def from_dto(cls, dto: CreateWarehouseResultDTO) -> Self:
        """Явно преобразует результат Application в HTTP-представление."""
        return cls(
            id=dto.id,
            code=dto.code,
            name=dto.name,
            is_active=dto.is_active,
            default_storage_location_id=dto.default_storage_location_id,
        )
