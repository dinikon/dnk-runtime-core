from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CompletePublicationInitializationCommand:
    """Описывает один шаг complete_publication_initialization, без session и HTTP Request."""

    tenant_id: UUID
    actor_id: UUID
    run_id: UUID
    sequence: int
