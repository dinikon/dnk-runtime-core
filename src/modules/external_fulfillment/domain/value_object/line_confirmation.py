from dataclasses import dataclass

from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
)
from src.modules.external_fulfillment.domain.value_object.identifier import (
    SupplierFulfillmentLineIdVO,
)
from src.modules.external_fulfillment.domain.value_object.quantity import (
    SupplierFulfillmentQuantityVO,
)
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentLineConfirmationVO:
    """Передаёт подтверждённое поставщиком количество и цену за базовую единицу."""

    line_id: SupplierFulfillmentLineIdVO
    quantity: SupplierFulfillmentQuantityVO
    price: MoneyVO | None

    def __post_init__(self) -> None:
        """Требует цену для положительного количества и пустую цену для нуля."""
        if (
            not isinstance(self.line_id, SupplierFulfillmentLineIdVO)
            or not isinstance(self.quantity, SupplierFulfillmentQuantityVO)
            or (self.quantity.value.is_zero() and self.price is not None)
            or (
                not self.quantity.value.is_zero()
                and (not isinstance(self.price, MoneyVO) or self.price.amount < 0)
            )
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Нужны ID, количество и цена только для положительного подтверждения."
            )
