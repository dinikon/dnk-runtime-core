from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InventoryItemDeletionUsage:
    """Передаёт доменной проверке факты использования в каталоге и партиях."""

    has_catalog_items: bool
    has_stock_lots: bool = False
