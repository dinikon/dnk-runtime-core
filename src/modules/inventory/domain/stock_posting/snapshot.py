from dataclasses import dataclass
from datetime import datetime

from src.modules.inventory.domain.policy.stock_posting import StockPostingPolicy
from src.modules.inventory.domain.stock_posting.entity.stock_ledger_entry import (
    StockLedgerEntry,
)
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.domain.stock_posting.value_object.operation_type import (
    StockOperationType,
)
from src.modules.inventory.domain.stock_posting.value_object.posting_source import (
    PostingSourceVO,
)


@dataclass(frozen=True, slots=True)
class StockPostingSnapshot:
    """Сохраняет неизменяемый состав исходного проведения для точной компенсации."""

    id: StockPostingIdVO
    source: PostingSourceVO
    operation_type: StockOperationType
    posted_at: datetime
    entries: tuple[StockLedgerEntry, ...]
    reversal_of_id: StockPostingIdVO | None

    def ensure_valid(self) -> None:
        """Проверяет состав снимка теми же правилами, что и собственное состояние проведения."""
        StockPostingPolicy.ensure_valid(
            identifier=self.id,
            source=self.source,
            operation_type=self.operation_type,
            posted_at=self.posted_at,
            entries=self.entries,
            reversal_of_id=self.reversal_of_id,
        )
