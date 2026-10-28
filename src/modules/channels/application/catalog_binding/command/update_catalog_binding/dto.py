from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateCatalogBindingResultDTO:
    """Результат сценария update_catalog_binding."""

    id: UUID
    revision: int
