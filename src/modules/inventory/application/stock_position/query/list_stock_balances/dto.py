from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListStockBalancesItemDTO:
    """Передаёт сумму одной группы, не выдавая её за отдельную физическую позицию."""

    key: str
    inventory_item_id: UUID
    sku: str
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    warehouse_is_active: bool
    location_id: UUID
    location_code: str
    location_name: str
    location_is_active: bool
    owner_id: UUID
    owner_name: str | None
    lot_id: UUID | None
    lot_number: str | None
    serial_id: UUID | None
    serial_number: str | None
    stock_status: str
    base_uom: str
    manufactured_on: date | None
    expires_on: date | None
    on_hand_qty: Decimal
    position_count: int
    lot_count: int
    serial_count: int


@dataclass(frozen=True, slots=True)
class ListStockBalancesResultDTO:
    """Возвращает страницу сводных остатков без суммирования разных SKU и единиц."""

    items: tuple[ListStockBalancesItemDTO, ...]
    total: int
    offset: int
    limit: int
