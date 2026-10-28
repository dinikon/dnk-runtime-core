from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateCatalogVariantResultDTO:
    """Идентичность созданного варианта и его родительской карточки."""

    id: UUID
    parent_id: UUID
