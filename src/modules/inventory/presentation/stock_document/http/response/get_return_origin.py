from pydantic import BaseModel
from decimal import Decimal
from uuid import UUID
from src.modules.inventory.application.stock_document.query.get_return_origin.dto import (
    GetReturnOriginResultDTO,
)


class GetReturnOriginLineResponse(BaseModel):
    """Сериализует собственный контракт фактической строки основания."""

    id: UUID
    position: int
    inventory_item_id: UUID
    sku: str
    base_uom: str
    quantity: Decimal
    returned_quantity: Decimal
    remaining_quantity: Decimal
    location_id: UUID
    location_code: str
    stock_status: str
    lot_id: UUID | None
    lot_number: str | None
    serial_id: UUID | None
    serial_number: str | None


class GetReturnOriginResponse(BaseModel):
    """Сериализует контекст создания возврата с точными десятичными количествами."""

    execution_id: UUID
    document_id: UUID
    operation_type: str
    direction: str
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    owner_id: UUID
    lines: tuple[GetReturnOriginLineResponse, ...]

    @classmethod
    def from_dto(cls, dto: GetReturnOriginResultDTO) -> "GetReturnOriginResponse":
        """Проверяет конкретный DTO собственной схемой сериализации."""
        return cls.model_validate(dto, from_attributes=True)
