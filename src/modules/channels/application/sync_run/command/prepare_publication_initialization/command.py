from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PreparePublicationInitializationCommand:
    """Описывает один шаг prepare_publication_initialization, без session и HTTP Request."""

    tenant_id: UUID
    run_id: UUID
    sequence: int
