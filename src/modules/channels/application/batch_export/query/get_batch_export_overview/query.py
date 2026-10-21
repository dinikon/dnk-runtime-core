from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetBatchExportOverviewQuery:
    """Описывает чтение настроек, состава и истории канала."""

    channel_id: UUID
    tenant_id: UUID
