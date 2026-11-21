from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SetCatalogItemSkuResultDTO:
    """Возвращает сохранённую ссылку и факт создания складской позиции."""

    item_id: UUID
    inventory_item_id: UUID | None
    sku: str | None
    inventory_item_created: bool
