from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ExecuteDailyExportCommand:
    """Передаёт календарное событие без пользовательских credentials."""

    tenant_id: UUID
    channel_id: UUID
    revision: int
    scheduled_at: datetime
