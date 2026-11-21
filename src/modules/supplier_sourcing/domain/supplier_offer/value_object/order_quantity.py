from dataclasses import dataclass
from decimal import Decimal

from src.modules.supplier_sourcing.domain.supplier_offer.error import (
    SupplierOrderQuantityError,
)


@dataclass(frozen=True, slots=True)
class SupplierOrderQuantityVO:
    """Задаёт положительное коммерческое количество в базовой единице предложения."""

    value: Decimal

    def __post_init__(self) -> None:
        """Требует конечный положительный Decimal без округления."""
        if (
            not isinstance(self.value, Decimal)
            or not self.value.is_finite()
            or self.value <= 0
        ):
            raise SupplierOrderQuantityError(
                "Коммерческое количество должно быть конечным положительным Decimal."
            )
