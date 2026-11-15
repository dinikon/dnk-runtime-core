from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from typing import Self
from pydantic import BaseModel
from src.modules.inventory.application.stock_posting.query.list_stock_movements.dto import (
    ListStockMovementsResultDTO,
)


class ListStockMovementsItemResponse(BaseModel):
    """Сериализует собственный HTTP-контракт учётной проекции."""

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


class MovementPositionSnapshotResponse(BaseModel):
    """Сериализует собственный HTTP-контракт учётной проекции."""

    id: UUID
    quantity: Decimal
    version: int


class ListStockMovementsResponse(BaseModel):
    """Сериализует собственный HTTP-контракт учётной проекции."""

    items: tuple[ListStockMovementsItemResponse, ...]
    total: int
    offset: int
    limit: int
    position: MovementPositionSnapshotResponse | None = None

    @classmethod
    def from_dto(cls, dto: ListStockMovementsResultDTO) -> Self:
        """Явно проверяет конкретный Application DTO своей схемой сериализации."""
        return cls.model_validate(dto, from_attributes=True)
