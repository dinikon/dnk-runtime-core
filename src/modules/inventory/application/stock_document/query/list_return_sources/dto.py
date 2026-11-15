from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReturnSourceItemDTO:
    """Показывает физическое количество выбранного источника без коммерческой доступности."""

    id: UUID
    inventory_item_id: UUID
    location_id: UUID
    location_code: str
    stock_status: str
    lot_id: UUID | None
    lot_number: str | None
    serial_id: UUID | None
    serial_number: str | None
    manufactured_on: date | None
    expires_on: date | None
    base_uom: str
    on_hand_quantity: Decimal
    version: int


@dataclass(frozen=True, slots=True)
class ListReturnSourcesResultDTO:
    """Возвращает страницу физических источников и точный total."""

    items: tuple[ReturnSourceItemDTO, ...]
    total: int
    offset: int
    limit: int
