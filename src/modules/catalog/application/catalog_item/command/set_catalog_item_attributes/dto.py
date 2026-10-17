from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetCatalogItemAttributesResultDTO:
    """Результат сценария set_catalog_item_attributes: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
