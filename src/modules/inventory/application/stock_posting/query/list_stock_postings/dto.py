from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListStockPostingsItemDTO:
    """Передаёт собственную типизированную проекцию сценария."""

    id: UUID
    execution_id: UUID
    document_id: UUID
    document_status: str
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    owner_id: UUID
    owner_name: str | None
    operation_type: str
    posted_at: datetime
    entry_count: int


@dataclass(frozen=True, slots=True)
class ListStockPostingsResultDTO:
    """Возвращает страницу конкретного сценария физического учёта."""

    items: tuple[ListStockPostingsItemDTO, ...]
    total: int
    offset: int
    limit: int
