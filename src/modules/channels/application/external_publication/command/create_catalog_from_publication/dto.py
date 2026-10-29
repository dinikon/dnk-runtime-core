from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateCatalogFromPublicationResultDTO:
    """Возвращает созданный или уже связанный товар и безопасные предупреждения."""

    catalog_item_id: UUID
    binding_group_id: UUID
    created: bool
    warnings: tuple[str, ...] = ()
