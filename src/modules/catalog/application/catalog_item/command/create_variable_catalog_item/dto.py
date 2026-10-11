from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateVariableCatalogItemResultDTO:
    """Подтверждённая идентичность созданной семьи."""

    id: UUID
    root_revision: int
    child_ids: tuple[UUID, ...]
