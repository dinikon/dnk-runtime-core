from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.application.publication_import_run.port.source import (
    PublicationSourcePage,
)


@dataclass(frozen=True, slots=True)
class ImportPublicationPageCommand:
    """Передаёт параметры фонового сценария import_publication_page и lease."""

    tenant_id: UUID
    channel_id: UUID
    run_id: UUID
    job_id: UUID
    lock_token: str
    page: PublicationSourcePage
    expected_pages: int
