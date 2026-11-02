from decimal import Decimal

from src.modules.inventory.domain.error import (
    InvalidQuantityError,
    InvalidQuantityRulesError,
    QuantityStepError,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO


class QuantityValidationPolicy:
    """Проверяет базовое количество по правилам товара без округления и I/O."""

    @staticmethod
    def validate(*, quantity: QuantityVO, rules: QuantityRulesVO) -> None:
        """Принимает ноль и точные кратные шага без ограничения формата записи Decimal."""
        if not isinstance(quantity, QuantityVO):
            raise InvalidQuantityError(
                "Ожидалось типизированное количество QuantityVO."
            )
        if not isinstance(rules, QuantityRulesVO):
            raise InvalidQuantityRulesError("Ожидались правила QuantityRulesVO.")
        if quantity.value.is_zero():
            return
        coefficient, exponent = QuantityValidationPolicy._decimal_parts(quantity.value)
        step_coefficient, step_exponent = QuantityValidationPolicy._decimal_parts(
            rules.step
        )
        difference = exponent - step_exponent
        # После удаления конечных нулей меньший порядок не может дать целое кратное.
        # Модульная степень не разворачивает 10**difference даже для огромных порядков.
        if (
            difference < 0
            or (coefficient * pow(10, difference, step_coefficient)) % step_coefficient
        ):
            raise QuantityStepError(
                "Количество в базовой единице должно быть кратно шагу от нуля."
            )

    @staticmethod
    def _decimal_parts(value: Decimal) -> tuple[int, int]:
        """Выделяет целый коэффициент и порядок без конечных нулей и Decimal-арифметики."""
        parts = value.as_tuple()
        digits = list(parts.digits)
        exponent = int(parts.exponent)
        while len(digits) > 1 and digits[-1] == 0:
            digits.pop()
            exponent += 1
        coefficient = 0
        for digit in digits:
            coefficient = coefficient * 10 + digit
        return coefficient, exponent
