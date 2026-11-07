from src.modules.inventory.domain.stock_posting.issue_valuation_snapshot import (
    StockIssueValuationSnapshot,
)
from src.modules.inventory.domain.valuation_layer.error import (
    ValuationLayerIssueMismatchError,
    ValuationLayerTimeError,
)
from src.modules.inventory.domain.valuation_layer.receipt_snapshot import (
    ValuationLayerReceiptSnapshot,
)


class ValuationLayerIssuePolicy:
    """Проверяет применимость конкретного ISSUE к первоначальному основанию слоя без выбора FIFO."""

    @staticmethod
    def ensure_compatible(
        *, layer: ValuationLayerReceiptSnapshot, issue: StockIssueValuationSnapshot
    ) -> None:
        """Требует исходную позицию, одинаковые учётные измерения и приход не позже физического расхода."""
        if not isinstance(layer, ValuationLayerReceiptSnapshot) or not isinstance(
            issue, StockIssueValuationSnapshot
        ):
            raise ValuationLayerIssueMismatchError(
                "Нужны специализированные снимки слоя и расхода."
            )
        layer.ensure_valid()
        issue.ensure_valid()
        if (
            layer.source.position_id,
            layer.inventory_item_id,
            layer.owner_id,
            layer.warehouse_id,
            layer.base_uom,
        ) != (
            issue.position_id,
            issue.inventory_item_id,
            issue.owner_id,
            issue.warehouse_id,
            issue.base_uom,
        ):
            raise ValuationLayerIssueMismatchError(
                "ISSUE должен относиться к исходной позиции и тем же учётным измерениям слоя."
            )
        if issue.issued_at < layer.received_at:
            raise ValuationLayerTimeError(
                "Физический расход не может предшествовать поступлению слоя."
            )
