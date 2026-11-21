from dataclasses import dataclass
from decimal import Decimal

from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
)
from src.modules.external_fulfillment.domain.value_object.quantity import (
    SupplierFulfillmentQuantityVO,
)
from src.modules.shared.domain.decimal_arithmetic import is_decimal_multiple


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentQuantityTermsVO:
    """Хранит зафиксированные правила положительного количества по строке запроса."""

    step: Decimal
    minimum: Decimal
    multiple: Decimal

    def __post_init__(self) -> None:
        """Проверяет конечные положительные правила в базовой единице."""
        if any(
            not isinstance(value, Decimal) or not value.is_finite() or value <= 0
            for value in (self.step, self.minimum, self.multiple)
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Шаг, минимум и кратность должны быть конечными положительными Decimal."
            )

    def accepts(self, quantity: SupplierFulfillmentQuantityVO) -> bool:
        """Проверяет минимум и обе кратности без округления."""
        return (
            quantity.value >= self.minimum
            and is_decimal_multiple(quantity.value, self.step)
            and is_decimal_multiple(quantity.value, self.multiple)
        )
