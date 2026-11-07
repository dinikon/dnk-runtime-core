from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.valuation_layer_consumption import (
    ValuationLayerConsumptionPolicy,
)
from src.modules.inventory.domain.policy.valuation_layer_issue import (
    ValuationLayerIssuePolicy,
)
from src.modules.inventory.domain.stock_posting.issue_valuation_snapshot import (
    StockIssueValuationSnapshot,
)
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerConsumptionSnapshotError,
)
from src.modules.inventory.domain.valuation_layer.receipt_snapshot import (
    ValuationLayerReceiptSnapshot,
)
from src.modules.inventory.domain.valuation_layer.time import normalize_valuation_time
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class ValuationLayerConsumptionSnapshot:
    """Фиксирует проверяемый переход одного слоя по полной записи ISSUE без доказательства сохранения в БД."""

    layer: ValuationLayerReceiptSnapshot
    issue: StockIssueValuationSnapshot
    quantity: QuantityVO
    cost: MoneyVO
    remaining_qty_before: QuantityVO
    remaining_qty_after: QuantityVO
    remaining_cost_before: MoneyVO
    remaining_cost_after: MoneyVO
    version_before: int
    version_after: int
    updated_at_before: datetime
    consumed_at: datetime

    def ensure_valid(self) -> None:
        """Проверяет связь оснований, полный расход, накопленные денежные остатки, версии и UTC-хронологию."""
        ValuationLayerIssuePolicy.ensure_compatible(layer=self.layer, issue=self.issue)
        if (
            not isinstance(self.quantity, QuantityVO)
            or not isinstance(self.quantity.value, Decimal)
            or not self.quantity.value.is_finite()
            or self.quantity.value <= 0
            or self.quantity != self.issue.quantity
            or type(self.version_before) is not int
            or self.version_before < 0
            or type(self.version_after) is not int
            or self.version_after != self.version_before + 1
        ):
            raise InvalidValuationLayerConsumptionSnapshotError(
                "Нужны полное количество ISSUE и последовательные строгие версии слоя."
            )
        expected_before = ValuationLayerConsumptionPolicy.calculate_remaining_cost(
            cost_basis=self.layer.cost_basis,
            remaining_qty=self.remaining_qty_before,
        )
        expected_after = ValuationLayerConsumptionPolicy.calculate_remaining_cost(
            cost_basis=self.layer.cost_basis,
            remaining_qty=self.remaining_qty_after,
        )
        if (
            self.remaining_qty_before.value < self.quantity.value
            or QuantityArithmeticPolicy.subtract(
                self.remaining_qty_before, self.quantity
            )
            != self.remaining_qty_after
        ):
            raise InvalidValuationLayerConsumptionSnapshotError(
                "Уменьшение остатка должно точно соответствовать полной записи ISSUE."
            )
        for value in (self.cost, self.remaining_cost_before, self.remaining_cost_after):
            if (
                not isinstance(value, MoneyVO)
                or not isinstance(value.amount, Decimal)
                or not value.amount.is_finite()
            ):
                raise InvalidValuationLayerConsumptionSnapshotError(
                    "Нужны конечные MoneyVO стоимости потребления и обоих остатков."
                )
        if (
            self.remaining_cost_before != expected_before
            or self.remaining_cost_after != expected_after
            or self.cost != self.remaining_cost_before - self.remaining_cost_after
        ):
            raise InvalidValuationLayerConsumptionSnapshotError(
                "Стоимость потребления и остатки должны соответствовать накопленной формуле в исходной валюте."
            )
        normalize_valuation_time(self.updated_at_before)
        normalize_valuation_time(self.consumed_at)
        if (
            self.updated_at_before.utcoffset() != timedelta(0)
            or self.consumed_at.utcoffset() != timedelta(0)
            or self.updated_at_before < self.layer.created_at
            or self.consumed_at < self.updated_at_before
            or self.consumed_at < self.issue.issued_at
        ):
            raise InvalidValuationLayerConsumptionSnapshotError(
                "Переход хранит UTC-время не раньше создания, предыдущего изменения и физического расхода."
            )
