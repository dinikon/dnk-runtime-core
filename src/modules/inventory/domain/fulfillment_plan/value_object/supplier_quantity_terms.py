from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.fulfillment_plan.error import (
    FulfillmentSupplierOrderAssignmentError,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.shared.domain.decimal_arithmetic import is_decimal_multiple


@dataclass(frozen=True, slots=True)
class FulfillmentSupplierQuantityTermsVO:
    """Фиксирует правила количества внешней строки в момент её закрепления."""

    step: Decimal
    minimum: Decimal
    multiple: Decimal

    def __post_init__(self) -> None:
        """Проверяет конечные положительные правила в базовой единице."""
        if any(
            not isinstance(value, Decimal) or not value.is_finite() or value <= 0
            for value in (self.step, self.minimum, self.multiple)
        ):
            raise FulfillmentSupplierOrderAssignmentError(
                "Шаг, минимум и кратность должны быть конечными положительными Decimal."
            )

    def accepts(self, quantity: QuantityVO) -> bool:
        """Проверяет минимум и обе кратности без округления."""
        return (
            quantity.value >= self.minimum
            and is_decimal_multiple(quantity.value, self.step)
            and is_decimal_multiple(quantity.value, self.multiple)
        )
