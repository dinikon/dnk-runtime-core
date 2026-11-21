from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)


@dataclass(frozen=True, slots=True)
class CancelStatusChangeDocumentLineDTO:
    """Передаёт исторический план строки без текущих настроек SKU."""

    id: UUID
    position: int
    inventory_item_id: UUID
    sku: str
    base_uom: str
    planned_qty: Decimal
    source_quantity: Decimal
    source_uom: str
    factor_to_base: Decimal
    executed_qty: Decimal
    remaining_qty: Decimal


@dataclass(frozen=True, slots=True)
class CancelStatusChangeDocumentResultDTO:
    """Возвращает реквизиты изменения состояния и сохранённые строки."""

    id: UUID
    operation_type: StockOperationType
    status: StockDocumentStatus
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    owner_id: UUID
    owner_name: str | None
    reason: str
    target_status: str
    source_system: str | None
    source_reference: str | None
    source_version: int | None
    created_at: datetime
    updated_at: datetime
    version: int
    lines: tuple[CancelStatusChangeDocumentLineDTO, ...]
