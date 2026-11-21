from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListStockExecutionsItemDTO:
    """Передаёт собственную типизированную проекцию сценария."""

    id: UUID
    document_id: UUID
    document_status: str
    document_version: int
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    owner_id: UUID
    owner_name: str | None
    operation_type: str
    executed_at: datetime
    posting_id: UUID | None
    line_count: int


@dataclass(frozen=True, slots=True)
class ListStockExecutionsResultDTO:
    """Возвращает страницу конкретного сценария физического учёта."""

    items: tuple[ListStockExecutionsItemDTO, ...]
    total: int
    offset: int
    limit: int
