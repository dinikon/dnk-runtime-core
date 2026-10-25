from dataclasses import dataclass
from uuid import UUID
from src.modules.catalog.application.catalog_import.contracts import SourceRecord
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery


@dataclass(frozen=True, slots=True)
class ProcessCatalogImportRowCommand:
    """Вход отдельного сценария process_catalog_import_row."""

    import_id: UUID
    row: SourceRecord
    galleries: dict[str, CatalogItemGallery]
    warnings: tuple[str, ...]
