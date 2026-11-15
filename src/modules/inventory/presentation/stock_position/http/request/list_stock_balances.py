from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ListStockBalancesRequest(BaseModel):
    """Проверяет форму фильтров и ограниченную пагинацию до Application."""

    model_config = ConfigDict(extra="forbid")
    warehouse_id: UUID | None = None
    location_id: UUID | None = None
    owner_id: UUID | None = None
    inventory_item_id: UUID | None = None
    lot_id: UUID | None = None
    serial_id: UUID | None = None
    position_id: UUID | None = None
    stock_status: Literal["SELLABLE", "QUARANTINE", "DAMAGED", "BLOCKED"] | None = None
    search: str | None = Field(default=None, max_length=128)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    include_zero: bool = False

    group_by_lot: bool = False
    group_by_serial: bool = False
