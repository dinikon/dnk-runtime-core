from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LockCatalogItemForBindingResultDTO:
    """Возвращает конкретный результат сценария lock_catalog_item_for_binding."""

    id: UUID
    status: str
