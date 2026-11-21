from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Self
from pydantic import BaseModel
from src.modules.inventory.application.stock_execution.query.get_stock_execution_details.dto import (
    GetStockExecutionDetailsResultDTO,
)


class GetStockExecutionDetailsLineResponse(BaseModel):
    """Сериализует собственный HTTP-контракт учётной проекции."""

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
    destination_stock_status: str | None = None
    origin_execution_line_id: UUID | None = None
    source_ledger_entry_id: UUID | None = None
    destination_ledger_entry_id: UUID | None = None


class GetStockExecutionDetailsEntryResponse(BaseModel):
    """Сериализует собственный HTTP-контракт учётной проекции."""

    id: UUID
    position_id: UUID
    quantity_delta: Decimal
    base_uom: str
    execution_line_ids: tuple[UUID, ...]


class GetStockExecutionDetailsAllocationResponse(BaseModel):
    """Сериализует собственный HTTP-контракт учётной проекции."""

    execution_line_id: UUID
    amount: Decimal


class GetStockExecutionDetailsCostResponse(BaseModel):
    """Сериализует собственный HTTP-контракт учётной проекции."""

    id: UUID
    amount: Decimal
    currency: str
    basis_kind: str
    source_system: str | None
    source_reference: str | None
    allocations: tuple[GetStockExecutionDetailsAllocationResponse, ...]


class GetStockExecutionDetailsResponse(BaseModel):
    """Сериализует собственный HTTP-контракт учётной проекции."""

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
    lines: tuple[GetStockExecutionDetailsLineResponse, ...]
    ledger: tuple[GetStockExecutionDetailsEntryResponse, ...]
    costs: tuple[GetStockExecutionDetailsCostResponse, ...]

    write_off_reason: str | None = None
    operation_reason: str | None = None
    return_direction: str | None = None
    origin_execution_id: UUID | None = None
    target_status: str | None = None

    @classmethod
    def from_dto(cls, dto: GetStockExecutionDetailsResultDTO) -> Self:
        """Явно проверяет конкретный Application DTO своей схемой сериализации."""
        return cls.model_validate(dto, from_attributes=True)
