from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartCatalogImportResultDTO:
    """Результат отдельного сценария start_catalog_import."""

    id: UUID
    status: str
