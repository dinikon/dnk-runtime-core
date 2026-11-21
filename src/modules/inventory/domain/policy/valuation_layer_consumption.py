from decimal import Decimal

from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationLayerValueError,
)
from src.modules.inventory.domain.valuation_layer.value_object.cost_basis import (
    CostBasisVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.shared.domain.value_object.money import MoneyVO


class ValuationLayerConsumptionPolicy:
    """Оценивает остаток по накопленному расходу от первоначальной стоимости слоя."""

    @staticmethod
    def calculate_remaining_cost(
        *, cost_basis: CostBasisVO, remaining_qty: QuantityVO
    ) -> MoneyVO:
        """Округляет накопленную стоимость расхода HALF_UP до четырёх знаков без влияния Decimal context."""
        if not isinstance(cost_basis, CostBasisVO):
            raise InvalidValuationLayerValueError("Нужен CostBasisVO исходного слоя.")
        cost_basis.ensure_valid()
        if (
            not isinstance(remaining_qty, QuantityVO)
            or not isinstance(remaining_qty.value, Decimal)
            or not remaining_qty.value.is_finite()
            or remaining_qty.value < 0
            or remaining_qty.value > cost_basis.quantity.value
        ):
            raise InvalidValuationLayerValueError(
                "Остаток QuantityVO должен быть от нуля до первоначального количества."
            )

        # Все отношения точные; округляется только накопленная денежная сумма.
        qty_n, qty_d = cost_basis.quantity.value.as_integer_ratio()
        remaining_n, remaining_d = remaining_qty.value.as_integer_ratio()
        cost_n, cost_d = cost_basis.total_cost.amount.as_integer_ratio()
        total_units = cost_n * 10000 // cost_d
        numerator = total_units * (qty_n * remaining_d - remaining_n * qty_d)
        denominator = qty_n * remaining_d
        consumed_units, remainder = divmod(numerator, denominator)
        if remainder * 2 >= denominator:
            consumed_units += 1
        remaining_units = total_units - consumed_units
        amount = Decimal((0, tuple(int(digit) for digit in str(remaining_units)), -4))
        return MoneyVO(amount, cost_basis.total_cost.currency)
