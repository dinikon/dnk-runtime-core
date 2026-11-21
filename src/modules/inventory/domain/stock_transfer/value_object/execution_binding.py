from dataclasses import dataclass

from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_transfer.error import (
    InvalidStockTransferExecutionBindingError,
)
from src.modules.inventory.domain.stock_transfer.value_object.line_id import (
    StockTransferLineIdVO,
)


@dataclass(frozen=True, slots=True)
class StockTransferExecutionBindingVO:
    """Назначает целую фактическую строку расхода или прихода одной строке перемещения."""

    execution_line_id: StockExecutionLineIdVO
    transfer_line_id: StockTransferLineIdVO

    def __post_init__(self) -> None:
        """Требует типизированные ID без отдельного пользовательского количества."""
        if not isinstance(
            self.execution_line_id, StockExecutionLineIdVO
        ) or not isinstance(self.transfer_line_id, StockTransferLineIdVO):
            raise InvalidStockTransferExecutionBindingError(
                "Нужны ID фактической строки и строки StockTransfer."
            )
