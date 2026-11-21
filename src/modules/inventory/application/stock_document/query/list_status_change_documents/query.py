from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from src.modules.inventory.domain.stock_document.value_object.status import (
    StockDocumentStatus,
)


@dataclass(frozen=True, slots=True)
class ListStatusChangeDocumentsQuery:
    """Задаёт буквальный поиск по историческому SKU, фильтры и страницу."""

    search: str | None = None
    warehouse_id: UUID | None = None
    owner_id: UUID | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    status: StockDocumentStatus | None = StockDocumentStatus.DRAFT
    offset: int = 0
    limit: int = 20
