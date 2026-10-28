from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateCatalogVariantResultDTO:
    """Подтверждение атомарного изменения товара во внешнем UoW."""

    id: UUID
