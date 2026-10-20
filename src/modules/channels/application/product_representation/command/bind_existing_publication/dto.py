from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BindExistingPublicationResultDTO:
    """Возвращает конкретный результат сценария bind_existing_publication."""

    catalog_item_id: UUID
    representation_id: UUID
    binding_id: UUID
    revision: int
