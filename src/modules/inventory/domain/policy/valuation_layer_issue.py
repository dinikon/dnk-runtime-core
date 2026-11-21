from decimal import Decimal

from src.modules.inventory.domain.stock_posting.issue_valuation_snapshot import (
    StockIssueValuationSnapshot,
)
from src.modules.inventory.domain.valuation_layer.error import (
    ValuationLayerIssueMismatchError,
    ValuationLayerTimeError,
    ValuationLayerConsumptionError,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.valuation_layer.basis_snapshot import (
    ValuationLayerBasisSnapshot,
)


class ValuationLayerIssuePolicy:
    """Проверяет применимость конкретного ISSUE к первоначальному основанию слоя без выбора FIFO."""

    @staticmethod
    def ensure_quantity(
        *, issue: StockIssueValuationSnapshot, quantity: QuantityVO
    ) -> None:
        """Требует положительную часть не больше ISSUE и запрещает деление серийного экземпляра."""
        if not isinstance(issue, StockIssueValuationSnapshot):
            raise ValuationLayerIssueMismatchError(
                "Нужен специализированный снимок расхода."
            )
        issue.ensure_valid()
        if (
            not isinstance(quantity, QuantityVO)
            or not isinstance(quantity.value, Decimal)
            or not quantity.value.is_finite()
            or quantity.value <= 0
            or quantity.value > issue.quantity.value
            or (issue.serial_id is not None and quantity != issue.quantity)
        ):
            raise ValuationLayerConsumptionError(
                "Нужна положительная часть не больше ISSUE; SERIAL потребляется только целиком."
            )

    @staticmethod
    def ensure_compatible(
        *, layer: ValuationLayerBasisSnapshot, issue: StockIssueValuationSnapshot
    ) -> None:
        """Требует позицию слоя, те же учётные измерения и доступность к моменту расхода."""
        if not isinstance(layer, ValuationLayerBasisSnapshot) or not isinstance(
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
                "ISSUE должен относиться к позиции и тем же учётным измерениям слоя."
            )
        if issue.issued_at < layer.available_at:
            raise ValuationLayerTimeError(
                "Физический расход не может предшествовать появлению слоя на позиции."
            )
