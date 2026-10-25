from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProcessCatalogImportBatchCommand:
    """Вход отдельного сценария process_catalog_import_batch."""

    import_id: UUID
    version: int
