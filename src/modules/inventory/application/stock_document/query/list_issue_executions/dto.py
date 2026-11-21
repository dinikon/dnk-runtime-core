from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListIssueExecutionLineDTO:
    """Передаёт вклад одного факта в конкретную строку плана в базовой единице."""

    document_line_id: UUID
    position: int
    sku: str
    base_uom: str
    quantity: Decimal
    allocation_count: int


@dataclass(frozen=True, slots=True)
class ListIssueExecutionItemDTO:
    """Показывает сохранённый факт и состояние плана на момент этой операции."""

    execution_id: UUID
    posting_id: UUID
    posted_at: datetime
    document_version_after: int
    document_status: str
    line_count: int
    lines: tuple[ListIssueExecutionLineDTO, ...]


@dataclass(frozen=True, slots=True)
class ListIssueExecutionsResultDTO:
    """Возвращает страницу истории одного документа без восстановления агрегатов."""

    items: tuple[ListIssueExecutionItemDTO, ...]
    total: int
    offset: int
    limit: int
