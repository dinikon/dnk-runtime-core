from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel
from src.modules.inventory.application.stock_posting.query.get_stock_posting.dto import (
    GetStockPostingResultDTO,
)


class GetStockPostingLineResponse(BaseModel):
    """Сериализует собственный HTTP-контракт исторического результата."""

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


class GetStockPostingPositionResponse(BaseModel):
    """Сериализует собственный HTTP-контракт исторического результата."""

    id: UUID
    base_uom: str
    before_quantity: Decimal
    delta: Decimal
    after_quantity: Decimal
    before_version: int
    after_version: int


class GetStockPostingEntryResponse(BaseModel):
    """Сериализует собственный HTTP-контракт исторического результата."""

    id: UUID
    position_id: UUID
    quantity_delta: Decimal
    base_uom: str


class GetStockPostingAllocationResponse(BaseModel):
    """Сериализует собственный HTTP-контракт исторического результата."""

    execution_line_id: UUID
    amount: Decimal


class GetStockPostingCostResponse(BaseModel):
    """Сериализует собственный HTTP-контракт исторического результата."""

    id: UUID
    amount: Decimal
    currency: str
    basis_kind: str
    source_system: str | None
    source_reference: str | None
    allocations: list[GetStockPostingAllocationResponse]


class GetStockPostingResponse(BaseModel):
    """Сериализует собственный HTTP-контракт исторического результата."""

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
    lines: list[GetStockPostingLineResponse]
    positions: list[GetStockPostingPositionResponse]
    ledger: list[GetStockPostingEntryResponse]
    costs: list[GetStockPostingCostResponse]

    @classmethod
    def from_dto(cls, dto: GetStockPostingResultDTO) -> "GetStockPostingResponse":
        """Явно переносит поля конкретного результата, сохраняя Decimal строками."""
        return cls(
            document_id=dto.document_id,
            document_version_before=dto.document_version_before,
            document_version_after=dto.document_version_after,
            document_status=dto.document_status,
            execution_id=dto.execution_id,
            posting_id=dto.posting_id,
            event_id=dto.event_id,
            actor_id=dto.actor_id,
            warehouse_id=dto.warehouse_id,
            warehouse_code=dto.warehouse_code,
            warehouse_name=dto.warehouse_name,
            owner_id=dto.owner_id,
            owner_name=dto.owner_name,
            posted_at=dto.posted_at,
            lines=[
                GetStockPostingLineResponse(
                    id=value.id,
                    client_line_id=value.client_line_id,
                    document_line_id=value.document_line_id,
                    inventory_item_id=value.inventory_item_id,
                    sku=value.sku,
                    base_uom=value.base_uom,
                    quantity=value.quantity,
                    source_quantity=value.source_quantity,
                    source_uom=value.source_uom,
                    factor_to_base=value.factor_to_base,
                    location_id=value.location_id,
                    location_code=value.location_code,
                    lot_id=value.lot_id,
                    lot_number=value.lot_number,
                    serial_id=value.serial_id,
                    serial_number=value.serial_number,
                    stock_status=value.stock_status,
                    position_id=value.position_id,
                    ledger_entry_id=value.ledger_entry_id,
                )
                for value in dto.lines
            ],
            positions=[
                GetStockPostingPositionResponse(
                    id=value.id,
                    base_uom=value.base_uom,
                    before_quantity=value.before_quantity,
                    delta=value.delta,
                    after_quantity=value.after_quantity,
                    before_version=value.before_version,
                    after_version=value.after_version,
                )
                for value in dto.positions
            ],
            ledger=[
                GetStockPostingEntryResponse(
                    id=value.id,
                    position_id=value.position_id,
                    quantity_delta=value.quantity_delta,
                    base_uom=value.base_uom,
                )
                for value in dto.ledger
            ],
            costs=[
                GetStockPostingCostResponse(
                    id=value.id,
                    amount=value.amount,
                    currency=value.currency,
                    basis_kind=value.basis_kind,
                    source_system=value.source_system,
                    source_reference=value.source_reference,
                    allocations=[
                        GetStockPostingAllocationResponse(
                            execution_line_id=a.execution_line_id, amount=a.amount
                        )
                        for a in value.allocations
                    ],
                )
                for value in dto.costs
            ],
        )
