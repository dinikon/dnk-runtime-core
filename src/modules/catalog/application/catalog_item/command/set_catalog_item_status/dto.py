from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetCatalogItemStatusResultDTO:
    """Результат сценария set_catalog_item_status: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
