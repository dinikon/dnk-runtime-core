from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetCatalogImportQuery:
    """Вход отдельного сценария get_catalog_import."""

    import_id: UUID
