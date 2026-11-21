from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetIssueExecutionLineDTO:
    """Передаёт конкретную проекцию сохранённого результата расхода."""

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


@dataclass(frozen=True, slots=True)
class GetIssueExecutionPositionDTO:
    """Передаёт конкретную проекцию сохранённого результата расхода."""

    id: UUID
    base_uom: str
    before_quantity: Decimal
    delta: Decimal
    after_quantity: Decimal
    before_version: int
    after_version: int


@dataclass(frozen=True, slots=True)
class GetIssueExecutionEntryDTO:
    """Передаёт конкретную проекцию сохранённого результата расхода."""

    id: UUID
    position_id: UUID
    quantity_delta: Decimal
    base_uom: str


@dataclass(frozen=True, slots=True)
class GetIssueExecutionResultDTO:
    """Передаёт конкретную проекцию сохранённого результата расхода."""

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
    posted_at: datetime
    lines: tuple[GetIssueExecutionLineDTO, ...]
    positions: tuple[GetIssueExecutionPositionDTO, ...]
    ledger: tuple[GetIssueExecutionEntryDTO, ...]
