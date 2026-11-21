from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.warehouse.query.list_warehouses.dto import (
    ListWarehousesResultDTO,
)


class WarehouseListItemResponse(BaseModel):
    """Описывает строку HTTP-списка складов без дочерних коллекций."""

    id: UUID
    code: str
    name: str
    is_active: bool
    default_storage_location_id: UUID | None


class ListWarehousesResponse(BaseModel):
    """Передаёт страницу HTTP-списка и параметры пагинации."""

    items: tuple[WarehouseListItemResponse, ...]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(cls, dto: ListWarehousesResultDTO) -> Self:
        """Явно преобразует строки проекции и метаданные страницы."""
        return cls(
            items=tuple(
                WarehouseListItemResponse(
                    id=item.id,
                    code=item.code,
                    name=item.name,
                    is_active=item.is_active,
                    default_storage_location_id=item.default_storage_location_id,
                )
                for item in dto.items
            ),
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )
