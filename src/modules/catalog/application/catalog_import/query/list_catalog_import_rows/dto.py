from dataclasses import dataclass
from src.modules.catalog.application.catalog_import.contracts import ImportRowResult


@dataclass(frozen=True, slots=True)
class ListCatalogImportRowsResultDTO:
    """Результат отдельного сценария list_catalog_import_rows."""

    items: tuple[ImportRowResult, ...]
    total: int
