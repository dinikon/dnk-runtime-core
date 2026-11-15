from src.modules.inventory.application.stock_document.query.preview_status_change.dto import (
    PreviewStatusChangeResultDTO,
)
from pydantic import BaseModel
from decimal import Decimal
from uuid import UUID


class StatusChangePreviewPositionResponse(BaseModel):
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


class PreviewStatusChangeResponse(BaseModel):
    """Возвращает проверенный расчёт без записи фактов или удержания количества."""

    document_id: UUID
    version: int
    reason: str
    target_status: str
    positions: tuple[StatusChangePreviewPositionResponse, ...]

    @classmethod
    def from_dto(
        cls, dto: PreviewStatusChangeResultDTO
    ) -> "PreviewStatusChangeResponse":
        """Явно сериализует собственный DTO read-only расчёта."""
        return cls.model_validate(dto, from_attributes=True)
