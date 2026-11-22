from uuid import UUID
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SetDefaultCatalogCategoryResultDTO:
    """Идентификатор выбранной категории по умолчанию."""

    id: UUID
