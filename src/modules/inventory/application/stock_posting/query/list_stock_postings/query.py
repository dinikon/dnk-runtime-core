from dataclasses import dataclass
from src.modules.inventory.application.accounting.filters import StockAccountingFilters


@dataclass(frozen=True, slots=True)
class ListStockPostingsQuery:
    """Задаёт конкретный сценарий чтения физического учёта."""

    filters: StockAccountingFilters
    offset: int = 0
    limit: int = 20
