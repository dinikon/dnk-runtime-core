from datetime import date
from typing import Self, Literal
from uuid import UUID
from pydantic import BaseModel

from src.modules.inventory.application.stock_serial.query.list_stock_serials.dto import (
    ListStockSerialsResultDTO,
)


class ListStockSerialResponse(BaseModel):
    """Описывает строку HTTP-списка серийных экземпляров."""

    id: UUID
    inventory_item_id: UUID
    number: str
    lot_id: UUID | None
    lot_number: str | None
    date_source: Literal["NONE", "LOT"]
    manufactured_on: date | None
    expires_on: date | None


class ListStockSerialsResponse(BaseModel):
    """Описывает страницу серийных экземпляров с результатами серверной пагинации."""

    items: tuple[ListStockSerialResponse, ...]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(cls, dto: ListStockSerialsResultDTO) -> Self:
        """Явно преобразует строки и metadata страницы."""
        return cls(
            items=tuple(
                ListStockSerialResponse(
                    id=row.id,
                    inventory_item_id=row.inventory_item_id,
                    number=row.number,
                    lot_id=row.lot_id,
                    lot_number=row.lot_number,
                    date_source=row.date_source,
                    manufactured_on=row.manufactured_on,
                    expires_on=row.expires_on,
                )
                for row in dto.items
            ),
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )
