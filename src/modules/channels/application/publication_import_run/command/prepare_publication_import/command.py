from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PreparePublicationImportCommand:
    """Передаёт параметры фонового сценария prepare_publication_import и lease."""

    tenant_id: UUID
    channel_id: UUID
    run_id: UUID
    job_id: UUID
    lock_token: str
