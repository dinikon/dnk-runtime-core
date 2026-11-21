from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetReturnOriginLineDTO:
    """Показывает конкретную фактическую строку и независимый лимит её возврата."""

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


@dataclass(frozen=True, slots=True)
class GetReturnOriginResultDTO:
    """Возвращает контекст создания возврата без обещания текущего физического запаса."""

    execution_id: UUID
    document_id: UUID
    operation_type: str
    direction: str
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    owner_id: UUID
    lines: tuple[GetReturnOriginLineDTO, ...]
