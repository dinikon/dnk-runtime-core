from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PrepareCatalogImportResultDTO:
    """Результат отдельного сценария prepare_catalog_import."""

    id: UUID
    status: str
