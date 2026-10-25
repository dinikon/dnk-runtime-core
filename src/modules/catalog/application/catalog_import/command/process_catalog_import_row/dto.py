from dataclasses import dataclass
from src.modules.catalog.application.catalog_import.contracts import ImportRowResult


@dataclass(frozen=True, slots=True)
class ProcessCatalogImportRowResultDTO:
    """Результат отдельного сценария process_catalog_import_row."""

    result: ImportRowResult
    applied: bool = True
