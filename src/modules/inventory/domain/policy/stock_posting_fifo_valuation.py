from src.modules.inventory.domain.stock_posting.posting_fifo_plan_snapshot import (
    StockPostingFifoPlanSnapshot,
)
from src.modules.inventory.domain.stock_posting.snapshot import StockPostingSnapshot
from src.modules.inventory.domain.valuation_layer.consumption_snapshot import (
    ValuationLayerConsumptionSnapshot,
)
from src.modules.inventory.domain.valuation_layer.fifo_snapshot import (
    ValuationLayerFifoSnapshot,
)
from src.modules.inventory.domain.valuation_posting.error import (
    ValuationPostingSourceError,
)


class StockPostingFifoValuationPolicy:
    """Сверяет исторические результаты потребления с полным сохранённым FIFO-основанием проведения."""

    @staticmethod
    def ensure_consumptions(
        *,
        plan: StockPostingFifoPlanSnapshot,
        posting: StockPostingSnapshot,
        consumptions: tuple[ValuationLayerConsumptionSnapshot, ...],
    ) -> None:
        """Требует точное исходное проведение и взаимно однозначное соответствие результатов назначениям и состояниям кандидатов."""
        if (
            not isinstance(plan, StockPostingFifoPlanSnapshot)
            or not isinstance(posting, StockPostingSnapshot)
            or not isinstance(consumptions, tuple)
        ):
            raise ValuationPostingSourceError(
                "Нужны полный FIFO-план, снимок физического проведения и tuple результатов."
            )
        plan.ensure_valid()
        posting.ensure_valid()
        if posting != plan.posting:
            raise ValuationPostingSourceError(
                "Физическое проведение отличается от сохранённого FIFO-основания."
            )
        expected = {}
        for item in plan.plans:
            candidates = {
                candidate.layer.id: candidate for candidate in item.candidates
            }
            for allocation in item.allocations:
                expected[(item.issue.ledger_entry_id, allocation.layer_id)] = (
                    item.issue,
                    allocation,
                    candidates[allocation.layer_id],
                )
        actual = {}
        for consumption in consumptions:
            if not isinstance(consumption, ValuationLayerConsumptionSnapshot):
                raise ValuationPostingSourceError(
                    "Нужны специализированные результаты потребления."
                )
            consumption.ensure_valid()
            key = (consumption.issue.ledger_entry_id, consumption.layer.id)
            if key in actual:
                raise ValuationPostingSourceError(
                    "Результат назначения FIFO не должен повторяться."
                )
            actual[key] = consumption
        if set(actual) != set(expected):
            raise ValuationPostingSourceError(
                "Результаты должны покрывать ровно все назначения полного FIFO-плана."
            )
        for key, (issue, allocation, candidate) in expected.items():
            consumption = actual[key]
            before = ValuationLayerFifoSnapshot(
                consumption.layer,
                consumption.remaining_qty_before,
                consumption.remaining_cost_before,
                consumption.version_before,
                consumption.updated_at_before,
            )
            if (
                consumption.issue != issue
                or consumption.quantity != allocation.quantity
                or before != candidate
            ):
                raise ValuationPostingSourceError(
                    "Результат не соответствует назначению FIFO или исходному состоянию выбранного слоя."
                )
