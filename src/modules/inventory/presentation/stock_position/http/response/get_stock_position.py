from datetime import date
from decimal import Decimal
from uuid import UUID
from typing import Self
from pydantic import BaseModel
from src.modules.inventory.application.stock_position.query.get_stock_position.dto import (
    GetStockPositionResultDTO,
)


class GetStockPositionResponse(BaseModel):
    """Сериализует собственный HTTP-контракт учётной проекции."""

    id: UUID
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
    on_hand_qty: Decimal
    version: int
    ledger_quantity: Decimal

    @classmethod
    def from_dto(cls, dto: GetStockPositionResultDTO) -> Self:
        """Явно проверяет конкретный Application DTO своей схемой сериализации."""
        return cls.model_validate(dto, from_attributes=True)
