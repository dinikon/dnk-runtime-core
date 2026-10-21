from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartBatchExportCommand:
    """Описывает подтверждённое намерение обновить весь разрешённый состав подключения."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    run_id: UUID
    delivery_mode: str = "provider"
