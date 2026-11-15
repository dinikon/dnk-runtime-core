from src.modules.inventory.application.stock_document.query.preview_return.dto import (
    PreviewReturnResultDTO,
)
from pydantic import BaseModel
from decimal import Decimal
from uuid import UUID


class ReturnPreviewPositionResponse(BaseModel):
    """Показывает исходное и расчётное количество одной стороны, не выдавая временный ID за сохранённый."""

    id: UUID | None
    exists: bool
    role: str
    inventory_item_id: UUID
    sku: str
    location_id: UUID
    location_code: str
    stock_status: str
    lot_id: UUID | None
    lot_number: str | None
    serial_id: UUID | None
    serial_number: str | None
    base_uom: str
    before_quantity: Decimal
    delta: Decimal
    after_quantity: Decimal


class PreviewReturnResponse(BaseModel):
    """Возвращает проверенный расчёт без записи фактов или удержания количества."""

    document_id: UUID
    version: int
    reason: str
    direction: str
    origin_execution_id: UUID
    positions: tuple[ReturnPreviewPositionResponse, ...]

    @classmethod
    def from_dto(cls, dto: PreviewReturnResultDTO) -> "PreviewReturnResponse":
        """Явно сериализует собственный DTO read-only расчёта."""
        return cls.model_validate(dto, from_attributes=True)
