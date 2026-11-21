from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)


@dataclass(frozen=True, slots=True)
class ReceiptDocumentListItemDTO:
    """Проецирует реквизиты поступления без загрузки агрегата и всех строк."""

    id: UUID
    operation_type: StockOperationType
    status: StockDocumentStatus
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    owner_id: UUID
    owner_name: str | None
    source_system: str | None
    source_reference: str | None
    source_version: int | None
    created_at: datetime
    updated_at: datetime
    version: int
    line_count: int


@dataclass(frozen=True, slots=True)
class ListReceiptDocumentsResultDTO:
    """Возвращает страницу поступлений по единым фильтрам."""

    items: tuple[ReceiptDocumentListItemDTO, ...]
    total: int
    offset: int
    limit: int
