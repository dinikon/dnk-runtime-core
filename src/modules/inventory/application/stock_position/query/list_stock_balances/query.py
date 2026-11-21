from dataclasses import dataclass
from src.modules.inventory.application.accounting.filters import StockAccountingFilters


@dataclass(frozen=True, slots=True)
class ListStockBalancesQuery:
    """Задаёт сводку физических количеств с опциональной детализацией LOT/SERIAL."""

    filters: StockAccountingFilters
    offset: int = 0
    limit: int = 20
    include_zero: bool = False
    group_by_lot: bool = False
    group_by_serial: bool = False
