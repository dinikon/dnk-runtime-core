from dataclasses import dataclass
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
)
from src.modules.catalog.application.catalog_import.read_models import (
    ImportSummaryDTO,
    ImportAnalysisDTO,
)


@dataclass(frozen=True, slots=True)
class GetCatalogImportResultDTO:
    """Результат отдельного сценария get_catalog_import."""

    run: ImportSummaryDTO
    configuration: ImportConfiguration
    analysis: ImportAnalysisDTO
