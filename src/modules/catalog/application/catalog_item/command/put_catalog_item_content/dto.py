from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PutCatalogItemContentResultDTO:
    """Результат только сценария put_catalog_item_content после доменной проверки."""

    item_id: UUID
    root_id: UUID
    item_revision: int
    root_revision: int
