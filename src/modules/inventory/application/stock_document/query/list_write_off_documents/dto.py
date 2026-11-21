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
class WriteOffDocumentListItemDTO:
    """Проецирует реквизиты списания без загрузки агрегата и всех строк."""

    id: UUID
    operation_type: StockOperationType
    status: StockDocumentStatus
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    owner_id: UUID
    owner_name: str | None
    reason: str
    source_system: str | None
    source_reference: str | None
    source_version: int | None
    created_at: datetime
    updated_at: datetime
    version: int
    line_count: int


@dataclass(frozen=True, slots=True)
class ListWriteOffDocumentsResultDTO:
    """Возвращает страницу списаний по единым фильтрам."""

    items: tuple[WriteOffDocumentListItemDTO, ...]
    total: int
    offset: int
    limit: int
