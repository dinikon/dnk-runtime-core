from uuid import UUID
from typing import Literal, Self
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator


class ListStockMovementsRequest(BaseModel):
    """Проверяет форму фильтров и ограниченную пагинацию до Application."""

    model_config = ConfigDict(extra="forbid")
    warehouse_id: UUID | None = None
    location_id: UUID | None = None
    owner_id: UUID | None = None
    inventory_item_id: UUID | None = None
    lot_id: UUID | None = None
    serial_id: UUID | None = None
    position_id: UUID | None = None
    document_id: UUID | None = None
    execution_id: UUID | None = None
    posting_id: UUID | None = None
    stock_status: Literal["SELLABLE", "QUARANTINE", "DAMAGED", "BLOCKED"] | None = None
    operation_type: (
        Literal["RECEIPT", "ISSUE", "INTERNAL_MOVE", "ADJUSTMENT"] | None
    ) = None
    posted_from: AwareDatetime | None = None
    posted_to: AwareDatetime | None = None
    search: str | None = Field(default=None, max_length=128)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def ordered_period(self) -> Self:
        """Требует полуоткрытый период с началом раньше окончания."""
        if self.posted_from and self.posted_to and self.posted_from >= self.posted_to:
            raise ValueError("Начало периода должно быть раньше окончания.")
        return self
