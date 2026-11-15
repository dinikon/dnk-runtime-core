from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListStockMovementsItemDTO:
    """Передаёт собственную типизированную проекцию сценария."""

    id: UUID
    position_id: UUID
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
    document_id: UUID
    execution_id: UUID
    posting_id: UUID
    document_status: str
    operation_type: str
    posted_at: datetime
    quantity_delta: Decimal
    execution_line_ids: tuple[UUID, ...]
    historical_skus: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MovementPositionSnapshotDTO:
    """Фиксирует позицию, согласованную с прочитанной страницей истории."""

    id: UUID
    quantity: Decimal
    version: int


@dataclass(frozen=True, slots=True)
class ListStockMovementsResultDTO:
    """Возвращает страницу конкретного сценария физического учёта."""

    items: tuple[ListStockMovementsItemDTO, ...]
    total: int
    offset: int
    limit: int
    position: MovementPositionSnapshotDTO | None = None
