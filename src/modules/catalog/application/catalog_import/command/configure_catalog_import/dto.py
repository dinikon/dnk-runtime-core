from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ConfigureCatalogImportResultDTO:
    """Результат отдельного сценария configure_catalog_import."""

    id: UUID
    version: int
    status: str
