from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.inventory_item.error import (
    InvalidPackagingQuantityError,
)


@dataclass(frozen=True, slots=True)
class PackagingQuantityVO:
    """Положительное содержимое упаковки в явно заданной единице измерения."""

    value: Decimal

    def __post_init__(self) -> None:
        """Запрещает ноль, отрицательные, нечисловые значения и неявный float."""
        if (
            not isinstance(self.value, Decimal)
            or not self.value.is_finite()
            or self.value <= 0
        ):
            raise InvalidPackagingQuantityError(
                "Содержимое должно быть конечным положительным Decimal."
            )
