from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetFilesOverviewQuery:
    """Доверенный tenant и выбранные диски для общей сводки без поиска."""

    tenant_id: UUID
    bucket_ids: tuple[UUID, ...] = ()
