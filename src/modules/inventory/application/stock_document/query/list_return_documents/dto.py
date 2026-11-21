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
class ReturnDocumentListItemDTO:
    """Проецирует реквизиты возврата без загрузки агрегата и всех строк."""

    id: UUID
    operation_type: StockOperationType
    status: StockDocumentStatus
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    owner_id: UUID
    owner_name: str | None
    reason: str
    direction: str
    origin_execution_id: UUID
    source_system: str | None
    source_reference: str | None
    source_version: int | None
    created_at: datetime
    updated_at: datetime
    version: int
    line_count: int


@dataclass(frozen=True, slots=True)
class ListReturnDocumentsResultDTO:
    """Возвращает страницу изменений состояния по единым фильтрам."""

    items: tuple[ReturnDocumentListItemDTO, ...]
    total: int
    offset: int
    limit: int
