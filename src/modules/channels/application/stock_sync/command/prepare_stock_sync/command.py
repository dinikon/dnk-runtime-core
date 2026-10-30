from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PrepareStockSyncCommand:
    """Проверяет envelope текущего задания."""

    tenant_id: UUID
    channel_id: UUID
    publication_id: UUID
    operation_id: UUID
    lock_token: str
