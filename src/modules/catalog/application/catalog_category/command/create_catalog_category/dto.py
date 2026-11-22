from uuid import UUID
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateCatalogCategoryResultDTO:
    """Идентификатор созданного узла дерева."""

    id: UUID
