from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CleanupExpiredTrashCommand:
    """Передаёт неизменный cutoff и курсор ограниченной порции очистки."""

    tenant_id: UUID
    now: datetime
    after_id: UUID | None = None
    batch_size: int = 100
