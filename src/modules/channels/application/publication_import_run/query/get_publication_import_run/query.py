from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetPublicationImportRunQuery:
    """Передаёт параметры чтения get_publication_import_run в текущем tenant."""

    tenant_id: UUID
    channel_id: UUID
    run_id: UUID | None = None
