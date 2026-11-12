from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InventoryItemDeletionUsage:
    """Передаёт доменной проверке факт связи с любой карточкой каталога."""

    has_catalog_items: bool
