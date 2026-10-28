from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateCatalogBindingResultDTO:
    """Результат сценария create_catalog_binding."""

    id: UUID
    revision: int
