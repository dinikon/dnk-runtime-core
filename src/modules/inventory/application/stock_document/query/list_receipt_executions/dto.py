from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListReceiptExecutionLineDTO:
    """Передаёт вклад одного факта в конкретную строку плана в базовой единице."""

    document_line_id: UUID
    position: int
    sku: str
    base_uom: str
    quantity: Decimal
    allocation_count: int


@dataclass(frozen=True, slots=True)
class ListReceiptExecutionItemDTO:
    """Показывает сохранённый факт и состояние плана на момент этой операции."""

    execution_id: UUID
    posting_id: UUID
    posted_at: datetime
    document_version_after: int
    document_status: str
    line_count: int
    lines: tuple[ListReceiptExecutionLineDTO, ...]


@dataclass(frozen=True, slots=True)
class ListReceiptExecutionsResultDTO:
    """Возвращает страницу истории одного документа без восстановления агрегатов."""

    items: tuple[ListReceiptExecutionItemDTO, ...]
    total: int
    offset: int
    limit: int
