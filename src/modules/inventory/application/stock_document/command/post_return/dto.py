from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PostReturnLineDTO:
    """Передаёт конкретную проекцию сохранённого результата возврата."""

    id: UUID
    client_line_id: UUID
    document_line_id: UUID
    inventory_item_id: UUID
    sku: str
    base_uom: str
    quantity: Decimal
    source_quantity: Decimal
    source_uom: str
    factor_to_base: Decimal
    location_id: UUID
    location_code: str
    lot_id: UUID | None
    lot_number: str | None
    serial_id: UUID | None
    serial_number: str | None
    stock_status: str
    position_id: UUID
    ledger_entry_id: UUID
    origin_execution_line_id: UUID


@dataclass(frozen=True, slots=True)
class PostReturnPositionDTO:
    """Передаёт конкретную проекцию сохранённого результата возврата."""

    id: UUID
    base_uom: str
    before_quantity: Decimal
    delta: Decimal
    after_quantity: Decimal
    before_version: int
    after_version: int


@dataclass(frozen=True, slots=True)
class PostReturnEntryDTO:
    """Передаёт конкретную проекцию сохранённого результата возврата."""

    id: UUID
    position_id: UUID
    quantity_delta: Decimal
    base_uom: str


@dataclass(frozen=True, slots=True)
class PostReturnResultDTO:
    """Передаёт конкретную проекцию сохранённого результата возврата."""

    document_id: UUID
    document_version_before: int
    document_version_after: int
    document_status: str
    execution_id: UUID
    posting_id: UUID
    event_id: UUID
    actor_id: UUID
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    owner_id: UUID
    owner_name: str | None
    reason: str
    direction: str
    origin_execution_id: UUID
    posted_at: datetime
    lines: tuple[PostReturnLineDTO, ...]
    positions: tuple[PostReturnPositionDTO, ...]
    ledger: tuple[PostReturnEntryDTO, ...]
