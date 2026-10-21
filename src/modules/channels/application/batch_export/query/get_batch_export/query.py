from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetBatchExportQuery:
    """Описывает ограниченную страницу результатов пакета."""

    tenant_id: UUID
    run_id: UUID
    offset: int = 0
    limit: int = 50
