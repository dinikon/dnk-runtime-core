from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateCatalogItemResultDTO:
    """Результат сценария create_catalog_item: идентичность созданного товара."""

    id: UUID
