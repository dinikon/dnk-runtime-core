from dataclasses import dataclass
from typing import Self

from src.modules.inventory.domain.policy.stock_issue_fifo import StockIssueFifoPolicy
from src.modules.inventory.domain.stock_posting.issue_valuation_snapshot import (
    StockIssueValuationSnapshot,
)
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidStockIssueFifoPlanError,
)
from src.modules.inventory.domain.valuation_layer.fifo_snapshot import (
    ValuationLayerFifoSnapshot,
)
from src.modules.inventory.domain.valuation_layer.value_object.issue_allocation import (
    ValuationLayerIssueAllocationVO,
)


@dataclass(frozen=True, slots=True)
class StockIssueFifoPlanSnapshot:
    """Фиксирует воспроизводимый FIFO-план одной записи ISSUE относительно явно переданного пула."""

    issue: StockIssueValuationSnapshot
    candidates: tuple[ValuationLayerFifoSnapshot, ...]
    allocations: tuple[ValuationLayerIssueAllocationVO, ...]

    @classmethod
    def create(
        cls,
        *,
        issue: StockIssueValuationSnapshot,
        candidates: tuple[ValuationLayerFifoSnapshot, ...],
    ) -> Self:
        """Выводит назначения из кандидатов и проверяет целостность готового плана."""
        plan = cls(
            issue,
            candidates,
            StockIssueFifoPolicy.build_allocations(issue=issue, candidates=candidates),
        )
        plan.ensure_valid()
        return plan

    def ensure_valid(self) -> None:
        """Повторяет FIFO по сохранённому пулу и требует точные количества, порядок, ссылки и версии назначений."""
        if not isinstance(self.allocations, tuple):
            raise InvalidStockIssueFifoPlanError(
                "Назначения FIFO должны быть неизменяемым tuple."
            )
        for allocation in self.allocations:
            if not isinstance(allocation, ValuationLayerIssueAllocationVO):
                raise InvalidStockIssueFifoPlanError(
                    "Нужны типизированные назначения количества слоям."
                )
            allocation.ensure_valid()
        expected = StockIssueFifoPolicy.build_allocations(
            issue=self.issue, candidates=self.candidates
        )
        if self.allocations != expected:
            raise InvalidStockIssueFifoPlanError(
                "Назначения не соответствуют полному FIFO-расчёту по сохранённым кандидатам."
            )
