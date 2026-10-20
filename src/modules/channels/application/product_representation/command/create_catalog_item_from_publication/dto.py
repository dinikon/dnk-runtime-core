from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateCatalogItemFromPublicationResultDTO:
    """Возвращает конкретный результат сценария create_catalog_item_from_publication."""

    catalog_item_id: UUID
    representation_id: UUID
    binding_id: UUID
