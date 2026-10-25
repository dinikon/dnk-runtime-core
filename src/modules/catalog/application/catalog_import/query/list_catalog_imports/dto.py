from dataclasses import dataclass
from src.modules.catalog.application.catalog_import.read_models import ImportSummaryDTO


@dataclass(frozen=True, slots=True)
class ListCatalogImportsResultDTO:
    """Результат отдельного сценария list_catalog_imports."""

    items: tuple[ImportSummaryDTO, ...]
    total: int
