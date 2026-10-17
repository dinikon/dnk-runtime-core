from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateSimpleCatalogItemResultDTO:
    """Результат сценария create_simple_catalog_item: идентичность и новая ревизия товара."""

    id: UUID
    revision: int
