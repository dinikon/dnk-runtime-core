from dataclasses import dataclass
from datetime import date
from typing import Literal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StockSerialListItemDTO:
    """Передаёт проекцию экземпляра и актуальные даты связанной партии без ORM."""

    id: UUID
    inventory_item_id: UUID
    number: str
    lot_id: UUID | None
    lot_number: str | None
    date_source: Literal["NONE", "LOT"]
    manufactured_on: date | None
    expires_on: date | None


@dataclass(frozen=True, slots=True)
class ListStockSerialsResultDTO:
    """Передаёт страницу серийных экземпляров выбранного SKU."""

    items: tuple[StockSerialListItemDTO, ...]
    total: int
    offset: int
    limit: int
