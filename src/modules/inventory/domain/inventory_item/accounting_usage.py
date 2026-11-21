from dataclasses import dataclass
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO


@dataclass(frozen=True, slots=True)
class InventoryItemAccountingUsage:
    """Передаёт полные факты сохранённого учёта для проверки новых настроек."""

    has_history: bool
    quantities: tuple[QuantityVO, ...] = ()
    positive_lot_dates: tuple[StockDatesVO, ...] = ()
