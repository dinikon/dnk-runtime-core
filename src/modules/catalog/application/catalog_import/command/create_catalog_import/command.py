from dataclasses import dataclass
from uuid import UUID
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
)


@dataclass(frozen=True, slots=True)
class CreateCatalogImportCommand:
    """Вход отдельного сценария create_catalog_import."""

    tenant_id: UUID
    actor_id: UUID
    key: str
    fingerprint: str
    source_name: str
    source_url: str | None
    source_file_id: UUID | None
    configuration: ImportConfiguration
