from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InventoryItemDeletionUsage:
    """Передаёт доменной проверке факты использования в каталоге, партиях и серийных экземплярах."""

    has_catalog_items: bool
    has_stock_lots: bool = False
    has_stock_serials: bool = False
