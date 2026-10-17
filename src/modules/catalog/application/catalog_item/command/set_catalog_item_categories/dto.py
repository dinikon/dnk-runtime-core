from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetCatalogItemCategoriesResultDTO:
    """Результат сценария set_catalog_item_categories: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
