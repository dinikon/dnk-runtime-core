from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetCatalogItemTagsResultDTO:
    """Результат только сценария set_catalog_item_tags после доменной проверки."""

    item_id: UUID
    root_id: UUID
    item_revision: int
    root_revision: int
