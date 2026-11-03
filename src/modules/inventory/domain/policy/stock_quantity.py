from decimal import (
    Context,
    DecimalException,
    Inexact,
    InvalidOperation,
    MAX_EMAX,
    MIN_EMIN,
    Overflow,
    ROUND_HALF_EVEN,
    Underflow,
)

from src.modules.inventory.domain.error import (
    InvalidStockDeltaError,
    NegativeStockQuantityError,
    StockQuantityArithmeticError,
)
from src.modules.inventory.domain.policy.quantity_validation import (
    QuantityValidationPolicy,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO


class StockQuantityPolicy:
    """Точно применяет знаковое изменение к остатку без отрицательных значений и округления."""

    # Технический предел промежуточного результата защищает от разворачивания
    # огромного разрыва порядков. Inexact запрещает возвращать округлённое значение.
    _MAX_RESULT_DIGITS = 1_000_000

    @staticmethod
    def apply_delta(
        *, quantity: QuantityVO, delta: StockDeltaVO, rules: QuantityRulesVO
    ) -> QuantityVO:
        """Проверяет шаг текущего количества, модуля дельты и точного нового остатка."""
        if not isinstance(delta, StockDeltaVO):
            raise InvalidStockDeltaError("Ожидалось знаковое изменение StockDeltaVO.")
        QuantityValidationPolicy.validate(quantity=quantity, rules=rules)
        magnitude = QuantityVO(delta.value.copy_abs())
        QuantityValidationPolicy.validate(quantity=magnitude, rules=rules)
        if delta.value.is_zero():
            return quantity
        if delta.value.is_signed() and magnitude.value > quantity.value:
            raise NegativeStockQuantityError(
                "Изменение приводит к отрицательному физическому остатку."
            )
        if quantity.value.is_zero():
            return magnitude
        parts = (quantity.value.as_tuple(), delta.value.as_tuple())
        exponent = min(int(part.exponent) for part in parts)
        precision = (
            max(len(part.digits) + int(part.exponent) - exponent for part in parts) + 1
        )
        context = Context(
            prec=min(precision, StockQuantityPolicy._MAX_RESULT_DIGITS),
            Emin=MIN_EMIN,
            Emax=MAX_EMAX,
            rounding=ROUND_HALF_EVEN,
            traps=[InvalidOperation, Overflow, Underflow, Inexact],
        )
        try:
            result = context.add(quantity.value, delta.value)
        except DecimalException as exc:
            raise StockQuantityArithmeticError(
                "Результат невозможно безопасно представить без потери разрядов."
            ) from exc
        changed = QuantityVO(result)
        QuantityValidationPolicy.validate(quantity=changed, rules=rules)
        return changed
