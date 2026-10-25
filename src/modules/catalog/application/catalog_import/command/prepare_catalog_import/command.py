from dataclasses import dataclass
from uuid import UUID
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
)
from src.modules.catalog.application.catalog_import.read_models import ImportAnalysisDTO


@dataclass(frozen=True, slots=True)
class PrepareCatalogImportCommand:
    """Вход отдельного сценария prepare_catalog_import."""

    import_id: UUID
    version: int
    total: int
    configuration: ImportConfiguration
    analysis: ImportAnalysisDTO
