from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BindExistingPublicationCommand:
    """Задаёт конкретный вход сценария bind_existing_publication."""

    tenant_id: UUID
    actor_id: UUID
    publication_id: UUID
    catalog_item_id: UUID
    expected_revision: int | None
