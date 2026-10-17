from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CompletePublicationImportCommand:
    """Передаёт параметры фонового сценария complete_publication_import и lease."""

    tenant_id: UUID
    channel_id: UUID
    run_id: UUID
    job_id: UUID
    lock_token: str
    error_code: str | None
