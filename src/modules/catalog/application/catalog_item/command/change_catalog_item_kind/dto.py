from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ChangeCatalogItemKindResultDTO:
    """Результат только сценария change_catalog_item_kind после доменной проверки."""

    item_id: UUID
    root_id: UUID
    item_revision: int
    root_revision: int
    child_ids: tuple[UUID, ...]
