from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListCatalogImportRowsQuery:
    """Вход отдельного сценария list_catalog_import_rows."""

    import_id: UUID
    outcome: str | None = None
    offset: int = 0
    limit: int = 100
