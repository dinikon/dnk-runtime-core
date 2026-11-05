from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.policy.quantity_arithmetic import (
    QuantityArithmeticPolicy,
)
from src.modules.inventory.domain.policy.quantity_validation import (
    QuantityValidationPolicy,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO


class StockAdjustmentQuantityPolicy:
    """Применяет доказанную точную поправку, проверяя текущий шаг только для целевого остатка."""

    @staticmethod
    def apply(
        *,
        quantity: QuantityVO,
        expected_qty: QuantityVO,
        target_qty: QuantityVO,
        delta: StockDeltaVO,
        rules: QuantityRulesVO,
    ) -> QuantityVO:
        """Требует неизменный исходный остаток и точное равенство quantity + delta = target без округления."""
        if (
            not all(
                isinstance(value, QuantityVO)
                for value in (quantity, expected_qty, target_qty)
            )
            or not isinstance(delta, StockDeltaVO)
            or delta.value.is_zero()
        ):
            raise StockAdjustmentError(
                "Нужны исходный/целевой остатки и ненулевая знаковая поправка."
            )
        if quantity != expected_qty:
            raise StockAdjustmentError(
                "Текущий остаток изменился относительно основания поправки."
            )
        magnitude = QuantityVO(delta.value.copy_abs())
        actual = (
            QuantityArithmeticPolicy.subtract(quantity, magnitude)
            if delta.value.is_signed()
            else QuantityArithmeticPolicy.add(quantity, magnitude)
        )
        if actual != target_qty:
            raise StockAdjustmentError("Запись не приводит точно к целевому остатку.")
        QuantityValidationPolicy.validate(quantity=target_qty, rules=rules)
        return target_qty
