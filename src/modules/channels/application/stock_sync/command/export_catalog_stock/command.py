from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ExportCatalogStockCommand:
    """Намерение отправить количественный остаток выбранных связей."""

    tenant_id: UUID
    channel_id: UUID
    group_id: UUID
    publication_ids: tuple[UUID, ...] = ()
