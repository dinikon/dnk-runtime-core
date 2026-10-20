from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartPublicationImportCommand:
    """Запускает явную подготовку конкретной версии публикации."""

    tenant_id: UUID
    actor_id: UUID
    publication_id: UUID
    preparation_id: UUID
    expected_observed_revision: int
