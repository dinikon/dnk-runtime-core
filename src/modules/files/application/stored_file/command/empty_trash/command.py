from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EmptyTrashCommand:
    """Передаёт границу запрошенной очистки и keyset-курсор ограниченной порции."""

    tenant_id: UUID
    cutoff: datetime
    after_id: UUID | None = None
    batch_size: int = 100
