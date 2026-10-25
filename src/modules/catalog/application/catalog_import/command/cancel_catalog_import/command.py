from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CancelCatalogImportCommand:
    """Вход отдельного сценария cancel_catalog_import."""

    import_id: UUID
