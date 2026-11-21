from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.domain.stock_location.value_object.location_type import (
    LocationType,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.dto import (
    ListStockLocationsResultDTO,
)


class StockLocationListItemResponse(BaseModel):
    """Описывает строку плоского HTTP-списка локаций."""

    id: UUID
    warehouse_id: UUID
    parent_location_id: UUID | None
    code: str
    name: str
    location_type: LocationType
    is_active: bool


class ListStockLocationsResponse(BaseModel):
    """Передаёт страницу и параметры серверной пагинации."""

    items: tuple[StockLocationListItemResponse, ...]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(cls, dto: ListStockLocationsResultDTO) -> Self:
        """Явно преобразует все строки и метаданные страницы."""
        return cls(
            items=tuple(
                StockLocationListItemResponse(
                    id=item.id,
                    warehouse_id=item.warehouse_id,
                    parent_location_id=item.parent_location_id,
                    code=item.code,
                    name=item.name,
                    location_type=item.location_type,
                    is_active=item.is_active,
                )
                for item in dto.items
            ),
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )
