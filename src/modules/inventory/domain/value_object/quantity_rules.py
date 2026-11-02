from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.error import InvalidQuantityRulesError


@dataclass(frozen=True, slots=True)
class QuantityRulesVO:
    """Шаг от нуля и максимальное число дробных знаков в базовой единице товара."""

    step: Decimal
    precision: int

    def __post_init__(self) -> None:
        """Проверяет положительный шаг и его представимость без округления."""
        if (
            not isinstance(self.step, Decimal)
            or not self.step.is_finite()
            or self.step <= 0
            or type(self.precision) is not int
            or self.precision < 0
        ):
            raise InvalidQuantityRulesError(
                "Нужны конечный положительный Decimal-шаг и целая неотрицательная точность."
            )
        parts = self.step.as_tuple()
        fractional_digits = max(0, -int(parts.exponent))
        for digit in reversed(parts.digits):
            if digit != 0 or fractional_digits == 0:
                break
            fractional_digits -= 1
        if fractional_digits > self.precision:
            raise InvalidQuantityRulesError(
                "Шаг должен точно выражаться с заданной точностью."
            )
