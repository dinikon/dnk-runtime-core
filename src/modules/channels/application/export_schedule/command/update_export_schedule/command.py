from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateExportScheduleCommand:
    """Описывает явное изменение календарной policy канала."""

    tenant_id: UUID
    channel_id: UUID
    enabled: bool
    hour: int
    minute: int
    timezone: str
    expected_revision: int
