from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartCatalogImportCommand:
    """Вход отдельного сценария start_catalog_import."""

    import_id: UUID
    version: int
