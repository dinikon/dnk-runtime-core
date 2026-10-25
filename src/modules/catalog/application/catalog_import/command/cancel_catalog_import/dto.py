from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CancelCatalogImportResultDTO:
    """Результат отдельного сценария cancel_catalog_import."""

    id: UUID
    status: str
