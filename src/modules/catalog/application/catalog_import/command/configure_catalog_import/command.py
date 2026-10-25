from dataclasses import dataclass
from uuid import UUID
from src.modules.catalog.domain.catalog_import.value_object.configuration import (
    ImportConfiguration,
)


@dataclass(frozen=True, slots=True)
class ConfigureCatalogImportCommand:
    """Вход отдельного сценария configure_catalog_import."""

    import_id: UUID
    configuration: ImportConfiguration
