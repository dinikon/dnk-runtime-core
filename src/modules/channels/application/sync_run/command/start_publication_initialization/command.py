from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartPublicationInitializationCommand:
    """Описывает один шаг start_publication_initialization, без session и HTTP Request."""

    tenant_id: UUID
    actor_id: UUID
    connection_id: UUID
    request_key: UUID
