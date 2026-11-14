from datetime import date
from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.stock_lot.query.list_stock_lots.dto import (
    ListStockLotsResultDTO,
)


class ListStockLotResponse(BaseModel):
    """Описывает строку HTTP-списка партий."""

    id: UUID
    inventory_item_id: UUID
    number: str
    manufactured_on: date | None
    expires_on: date | None


class ListStockLotsResponse(BaseModel):
    """Описывает страницу партий с результатами серверной пагинации."""

    items: tuple[ListStockLotResponse, ...]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(cls, dto: ListStockLotsResultDTO) -> Self:
        """Явно преобразует строки и metadata страницы."""
        return cls(
            items=tuple(
                ListStockLotResponse(
                    id=row.id,
                    inventory_item_id=row.inventory_item_id,
                    number=row.number,
                    manufactured_on=row.manufactured_on,
                    expires_on=row.expires_on,
                )
                for row in dto.items
            ),
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )
