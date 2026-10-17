from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetCatalogItemVirtualResultDTO:
    """Результат сценария set_catalog_item_virtual: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
