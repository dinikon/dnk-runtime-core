from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PostStatusChangeLineDTO:
    """Передаёт конкретную проекцию сохранённого результата изменения состояния."""

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
    destination_location_id: UUID
    destination_location_code: str
    lot_id: UUID | None
    lot_number: str | None
    serial_id: UUID | None
    serial_number: str | None
    stock_status: str
    destination_stock_status: str
    position_id: UUID
    ledger_entry_id: UUID
    destination_position_id: UUID
    destination_ledger_entry_id: UUID


@dataclass(frozen=True, slots=True)
class PostStatusChangePositionDTO:
    """Передаёт конкретную проекцию сохранённого результата изменения состояния."""

    id: UUID
    base_uom: str
    before_quantity: Decimal
    delta: Decimal
    after_quantity: Decimal
    before_version: int
    after_version: int


@dataclass(frozen=True, slots=True)
class PostStatusChangeEntryDTO:
    """Передаёт конкретную проекцию сохранённого результата изменения состояния."""

    id: UUID
    position_id: UUID
    quantity_delta: Decimal
    base_uom: str


@dataclass(frozen=True, slots=True)
class PostStatusChangeResultDTO:
    """Передаёт конкретную проекцию сохранённого результата изменения состояния."""

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
    target_status: str
    posted_at: datetime
    lines: tuple[PostStatusChangeLineDTO, ...]
    positions: tuple[PostStatusChangePositionDTO, ...]
    ledger: tuple[PostStatusChangeEntryDTO, ...]
