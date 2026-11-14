from dataclasses import dataclass

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)


@dataclass(frozen=True, slots=True)
class ListStockLotsQuery:
    """Передаёт владельца, буквальный поиск и серверную пагинацию партий."""

    inventory_item_id: InventoryItemIdVO
    offset: int = 0
    limit: int = 50
    search: str | None = None
