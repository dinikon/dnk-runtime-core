from dataclasses import dataclass

from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.stock_execution.value_object.adjustment_route import (
    StockAdjustmentExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.domain.stock_posting.ledger_entry_snapshot import (
    StockLedgerEntrySnapshot,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)


@dataclass(frozen=True, slots=True)
class StockAdjustmentEntrySnapshot:
    """Связывает конкретную запись Ledger с проведением, исполнением и точным переходом остатка."""

    posting_id: StockPostingIdVO
    execution_id: StockExecutionIdVO
    entry: StockLedgerEntrySnapshot
    route: StockAdjustmentExecutionRouteVO

    def ensure_valid(self) -> None:
        """Проверяет типы, адресность и равенство знаковой записи исходной поправке."""
        if (
            not isinstance(self.posting_id, StockPostingIdVO)
            or not isinstance(self.execution_id, StockExecutionIdVO)
            or not isinstance(self.entry, StockLedgerEntrySnapshot)
            or not isinstance(self.route, StockAdjustmentExecutionRouteVO)
        ):
            raise StockAdjustmentError(
                "Нужна запись корректировки с типизированным происхождением и маршрутом."
            )
        self.entry.ensure_valid()
        if (
            self.entry.position_id != self.route.position_id
            or self.entry.quantity_delta != self.route.adjustment.quantity_delta
        ):
            raise StockAdjustmentError(
                "Запись Ledger не соответствует позиции, знаку или цели поправки."
            )
