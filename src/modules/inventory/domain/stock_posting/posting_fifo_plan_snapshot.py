from dataclasses import dataclass

from src.modules.inventory.domain.policy.stock_posting_fifo import (
    StockPostingFifoPolicy,
)
from src.modules.inventory.domain.stock_posting.fifo_plan_snapshot import (
    StockIssueFifoPlanSnapshot,
)
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot


@dataclass(frozen=True, slots=True)
class StockPostingFifoPlanSnapshot:
    """Сохраняет полный исходный Ledger и FIFO-план каждой записи без самостоятельного жизненного цикла."""

    posting: StockPostingSnapshot
    plans: tuple[StockIssueFifoPlanSnapshot, ...]

    def ensure_valid(self) -> None:
        """Проверяет обычный ISSUE, вложенные назначения и полное согласованное покрытие физического основания."""
        StockPostingFifoPolicy.ensure_plans(posting=self.posting, plans=self.plans)
