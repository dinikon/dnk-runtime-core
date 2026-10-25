from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProcessCatalogImportBatchResultDTO:
    """Результат отдельного сценария process_catalog_import_batch."""

    id: UUID
    processed: int
    finished: bool
