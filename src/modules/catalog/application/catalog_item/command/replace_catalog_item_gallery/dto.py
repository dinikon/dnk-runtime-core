from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReplaceCatalogItemGalleryResultDTO:
    """Результат только сценария replace_catalog_item_gallery после доменной проверки."""

    item_id: UUID
    root_id: UUID
    item_revision: int
    root_revision: int
