from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from src.modules.inventory.domain.policy.valuation_layer_consumption import (
    ValuationLayerConsumptionPolicy,
)
from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerFifoSnapshotError,
)
from src.modules.inventory.domain.valuation_layer.basis_snapshot import (
    ValuationLayerBasisSnapshot,
)
from src.modules.inventory.domain.valuation_layer.time import normalize_valuation_time
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class ValuationLayerFifoSnapshot:
    """Сохраняет первоначальное основание, доступный остаток и версию кандидата FIFO."""

    layer: ValuationLayerBasisSnapshot
    remaining_qty: QuantityVO
    remaining_cost: MoneyVO
    version: int
    updated_at: datetime

    def ensure_valid(self) -> None:
        """Проверяет исходное основание, накопленную стоимость остатка, строгую версию и UTC-хронологию."""
        if not isinstance(self.layer, ValuationLayerBasisSnapshot):
            raise InvalidValuationLayerFifoSnapshotError(
                "Нужен специализированный снимок первоначального основания слоя."
            )
        self.layer.ensure_valid()
        expected_cost = ValuationLayerConsumptionPolicy.calculate_remaining_cost(
            cost_basis=self.layer.cost_basis,
            remaining_qty=self.remaining_qty,
        )
        if (
            type(self.version) is not int
            or self.version < 0
            or not isinstance(self.remaining_cost, MoneyVO)
            or not isinstance(self.remaining_cost.amount, Decimal)
            or not self.remaining_cost.amount.is_finite()
            or self.remaining_cost != expected_cost
        ):
            raise InvalidValuationLayerFifoSnapshotError(
                "Кандидат требует строгую версию и согласованный денежный остаток в исходной валюте."
            )
        normalize_valuation_time(self.updated_at)
        if (
            self.updated_at.utcoffset() != timedelta(0)
            or self.updated_at < self.layer.created_at
        ):
            raise InvalidValuationLayerFifoSnapshotError(
                "Кандидат хранит UTC-время изменения не раньше регистрации слоя."
            )
