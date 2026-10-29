from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateCatalogFromPublicationCommand:
    """Создаёт и связывает Catalog из актуальной карточки источника."""

    tenant_id: UUID
    actor_id: UUID
    channel_id: UUID
    publication_id: UUID
