from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetStockPostingLineDTO:
    """Передаёт конкретную проекцию сохранённого результата поступления."""

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
class GetStockPostingPositionDTO:
    """Передаёт конкретную проекцию сохранённого результата поступления."""

    id: UUID
    base_uom: str
    before_quantity: Decimal
    delta: Decimal
    after_quantity: Decimal
    before_version: int
    after_version: int


@dataclass(frozen=True, slots=True)
class GetStockPostingEntryDTO:
    """Передаёт конкретную проекцию сохранённого результата поступления."""

    id: UUID
    position_id: UUID
    quantity_delta: Decimal
    base_uom: str


@dataclass(frozen=True, slots=True)
class GetStockPostingAllocationDTO:
    """Передаёт конкретную проекцию сохранённого результата поступления."""

    execution_line_id: UUID
    amount: Decimal


@dataclass(frozen=True, slots=True)
class GetStockPostingCostDTO:
    """Передаёт конкретную проекцию сохранённого результата поступления."""

    id: UUID
    amount: Decimal
    currency: str
    basis_kind: str
    source_system: str | None
    source_reference: str | None
    allocations: tuple[GetStockPostingAllocationDTO, ...]


@dataclass(frozen=True, slots=True)
class GetStockPostingResultDTO:
    """Передаёт конкретную проекцию сохранённого результата поступления."""

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
    lines: tuple[GetStockPostingLineDTO, ...]
    positions: tuple[GetStockPostingPositionDTO, ...]
    ledger: tuple[GetStockPostingEntryDTO, ...]
    costs: tuple[GetStockPostingCostDTO, ...]
