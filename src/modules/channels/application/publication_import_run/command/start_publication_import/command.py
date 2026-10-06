from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartPublicationImportCommand:
    """Передаёт намерение обновить публикации активного канала."""

    tenant_id: UUID
    channel_id: UUID
