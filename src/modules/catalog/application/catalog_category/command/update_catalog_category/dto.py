from uuid import UUID
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UpdateCatalogCategoryResultDTO:
    """Идентификатор изменённой категории."""

    id: UUID
