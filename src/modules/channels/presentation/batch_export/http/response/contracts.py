from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class BatchExportSummaryResponse(BaseModel):
    """Показывает безопасную проекцию состояния пакета."""

    id: UUID
    channel_id: UUID
    trigger: str
    status: str
    created_at: datetime
    updated_at: datetime
    error_code: str | None
    counts: dict[str, int]
    interrupted: bool
    delivery_mode: str


class ExportScheduleResponse(BaseModel):
    """Передаёт policy календарного запуска."""

    enabled: bool
    hour: int
    minute: int
    timezone: str
    revision: int
    next_at: datetime | None
