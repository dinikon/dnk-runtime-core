from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetStockPostingDetailsLineDTO:
    """Показывает неизменяемые количества и отдельно актуальные и исторические подписи."""

    id: UUID
    document_line_id: UUID
    inventory_item_id: UUID
    sku: str
    sku_at_document: str
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
    ledger_entry_ids: tuple[UUID, ...]
    sku_at_receipt: str | None
    serial_number_at_receipt: str | None
    location_code_at_receipt: str | None
    destination_location_id: UUID | None = None
    destination_location_code: str | None = None
    source_ledger_entry_id: UUID | None = None
    destination_ledger_entry_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class GetStockPostingDetailsEntryDTO:
    """Передаёт одну запись Ledger и полную принадлежность фактических строк."""

    id: UUID
    position_id: UUID
    quantity_delta: Decimal
    base_uom: str
    execution_line_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class GetStockPostingDetailsAllocationDTO:
    """Передаёт сохранённое распределение исходной суммы."""

    execution_line_id: UUID
    amount: Decimal


@dataclass(frozen=True, slots=True)
class GetStockPostingDetailsCostDTO:
    """Передаёт исходное основание стоимости из собственного хранения исполнения."""

    id: UUID
    amount: Decimal
    currency: str
    basis_kind: str
    source_system: str | None
    source_reference: str | None
    allocations: tuple[GetStockPostingDetailsAllocationDTO, ...]


@dataclass(frozen=True, slots=True)
class GetStockPostingDetailsResultDTO:
    """Возвращает полный путь учётного основания без восстановления агрегатов."""

    id: UUID
    execution_id: UUID
    posting_id: UUID | None
    document_id: UUID
    document_version_at_execution: int
    document_current_version: int
    document_current_status: str
    operation_type: str
    executed_at: datetime
    posted_at: datetime | None
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    owner_id: UUID
    owner_name: str | None
    has_receipt_result: bool
    lines: tuple[GetStockPostingDetailsLineDTO, ...]
    ledger: tuple[GetStockPostingDetailsEntryDTO, ...]
    costs: tuple[GetStockPostingDetailsCostDTO, ...]
