from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FindUsedImageFilesQuery:
    """Запрашивает факты использования Channels в уже привязанном tenant."""

    tenant_id: UUID
    file_ids: tuple[UUID, ...]
