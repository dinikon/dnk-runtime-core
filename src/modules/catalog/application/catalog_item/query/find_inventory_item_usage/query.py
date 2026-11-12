from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FindInventoryItemUsageQuery:
    """Запрашивает любую связь со складской позицией в текущем tenant."""

    inventory_item_id: UUID
