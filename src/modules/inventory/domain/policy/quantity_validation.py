from src.modules.inventory.domain.error import (
    InvalidQuantityError,
    InvalidQuantityRulesError,
    QuantityStepError,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.shared.domain.decimal_arithmetic import is_decimal_multiple


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
        if not is_decimal_multiple(quantity.value, rules.step):
            raise QuantityStepError(
                "Количество в базовой единице должно быть кратно шагу от нуля."
            )
