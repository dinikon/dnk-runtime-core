from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StockAccountingFilters:
    """Передаёт точные фильтры физических проекций без состояния доступности."""

    warehouse_id: UUID | None = None
    location_id: UUID | None = None
    owner_id: UUID | None = None
    inventory_item_id: UUID | None = None
    lot_id: UUID | None = None
    serial_id: UUID | None = None
    position_id: UUID | None = None
    document_id: UUID | None = None
    execution_id: UUID | None = None
    posting_id: UUID | None = None
    stock_status: str | None = None
    operation_type: str | None = None
    posted_from: datetime | None = None
    posted_to: datetime | None = None
    search: str | None = None
