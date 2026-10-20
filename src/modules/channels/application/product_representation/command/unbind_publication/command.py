from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UnbindPublicationCommand:
    """Задаёт конкретный вход сценария unbind_publication."""

    tenant_id: UUID
    actor_id: UUID
    publication_id: UUID
    binding_id: UUID
    expected_revision: int
