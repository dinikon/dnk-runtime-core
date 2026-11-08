from dataclasses import dataclass
from decimal import Decimal

from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
)


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentQuantityVO:
    """Хранит точное неотрицательное количество для внешнего исполнения."""

    value: Decimal

    def __post_init__(self) -> None:
        """Требует конечный неотрицательный Decimal без округления."""
        if (
            not isinstance(self.value, Decimal)
            or not self.value.is_finite()
            or self.value < 0
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Количество должно быть конечным неотрицательным Decimal."
            )
