from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetCatalogItemMeasurementsResultDTO:
    """Результат только сценария set_catalog_item_measurements после доменной проверки."""

    item_id: UUID
    root_id: UUID
    item_revision: int
    root_revision: int
