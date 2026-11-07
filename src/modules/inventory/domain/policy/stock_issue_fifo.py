from decimal import Decimal

from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.valuation_layer_issue import (
    ValuationLayerIssuePolicy,
)
from src.modules.inventory.domain.stock_posting.issue_valuation_snapshot import (
    StockIssueValuationSnapshot,
)
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidStockIssueFifoPlanError,
    InsufficientValuationFifoQuantityError,
)
from src.modules.inventory.domain.valuation_layer.fifo_snapshot import (
    ValuationLayerFifoSnapshot,
)
from src.modules.inventory.domain.valuation_layer.value_object.issue_allocation import (
    ValuationLayerIssueAllocationVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO


class StockIssueFifoPolicy:
    """Выбирает количества слоёв одной исходной позиции по времени поступления без I/O и изменения остатков."""

    @staticmethod
    def build_allocations(
        *,
        issue: StockIssueValuationSnapshot,
        candidates: tuple[ValuationLayerFifoSnapshot, ...],
    ) -> tuple[ValuationLayerIssueAllocationVO, ...]:
        """Проверяет весь пул и возвращает полный FIFO-отбор с фиксированными версиями или отклоняет недостаток."""
        if not isinstance(issue, StockIssueValuationSnapshot) or not isinstance(
            candidates, tuple
        ):
            raise InvalidStockIssueFifoPlanError(
                "Нужны основание ISSUE и tuple снимков кандидатов."
            )
        issue.ensure_valid()
        identifiers = set()
        sources = set()
        for candidate in candidates:
            if not isinstance(candidate, ValuationLayerFifoSnapshot):
                raise InvalidStockIssueFifoPlanError(
                    "Пул содержит только специализированные снимки кандидатов FIFO."
                )
            candidate.ensure_valid()
            source = (
                candidate.layer.source.posting_id,
                candidate.layer.source.ledger_entry_id,
            )
            if candidate.layer.id in identifiers or source in sources:
                raise InvalidStockIssueFifoPlanError(
                    "Слой и его входящая запись Ledger не должны повторяться в пуле FIFO."
                )
            identifiers.add(candidate.layer.id)
            sources.add(source)
            ValuationLayerIssuePolicy.ensure_compatible(
                layer=candidate.layer, issue=issue
            )
            if issue.serial_id is not None and (
                candidate.layer.cost_basis.quantity.value != 1
                or candidate.remaining_qty.value not in (Decimal(0), Decimal(1))
            ):
                raise InvalidStockIssueFifoPlanError(
                    "Серийный кандидат имеет исходную одну PCS и целый остаток ноль или один."
                )
        remaining = issue.quantity
        allocations = []
        for candidate in sorted(
            candidates,
            key=lambda value: (value.layer.received_at, value.layer.id.uuid.int),
        ):
            if remaining.value == 0:
                break
            if candidate.remaining_qty.value == 0:
                continue
            quantity = QuantityVO(min(candidate.remaining_qty.value, remaining.value))
            ValuationLayerIssuePolicy.ensure_quantity(issue=issue, quantity=quantity)
            allocations.append(
                ValuationLayerIssueAllocationVO(
                    candidate.layer.id, quantity, candidate.version
                )
            )
            remaining = QuantityArithmeticPolicy.subtract(remaining, quantity)
        if remaining.value != 0:
            raise InsufficientValuationFifoQuantityError(
                "Кандидатов недостаточно для полного количества ISSUE; частичный план не создаётся."
            )
        return tuple(allocations)
