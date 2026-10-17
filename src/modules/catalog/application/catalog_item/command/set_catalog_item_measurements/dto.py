from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetCatalogItemMeasurementsResultDTO:
    """Результат сценария set_catalog_item_measurements: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
