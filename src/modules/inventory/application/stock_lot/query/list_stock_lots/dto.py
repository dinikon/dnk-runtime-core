from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StockLotListItemDTO:
    """Представляет строку списка партий без восстановления агрегата."""

    id: UUID
    inventory_item_id: UUID
    number: str
    manufactured_on: date | None
    expires_on: date | None


@dataclass(frozen=True, slots=True)
class ListStockLotsResultDTO:
    """Передаёт страницу партий и параметры серверной пагинации."""

    items: tuple[StockLotListItemDTO, ...]
    total: int
    offset: int
    limit: int
