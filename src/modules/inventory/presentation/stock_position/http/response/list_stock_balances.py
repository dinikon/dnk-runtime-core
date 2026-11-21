from datetime import date
from decimal import Decimal
from uuid import UUID
from typing import Self
from pydantic import BaseModel
from src.modules.inventory.application.stock_position.query.list_stock_balances.dto import (
    ListStockBalancesResultDTO,
)


class ListStockBalancesItemResponse(BaseModel):
    """Сериализует строку сводного физического остатка."""

    key: str
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
    position_count: int
    lot_count: int
    serial_count: int


class ListStockBalancesResponse(BaseModel):
    """Передаёт собственную страницу сводки и её total."""

    items: tuple[ListStockBalancesItemResponse, ...]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(cls, dto: ListStockBalancesResultDTO) -> Self:
        """Проверяет конкретный Application DTO схемой этого сценария."""
        return cls.model_validate(dto, from_attributes=True)
