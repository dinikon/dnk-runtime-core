from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.error import InvalidQuantityError


@dataclass(frozen=True, slots=True)
class QuantityVO:
    """Конечное неотрицательное количество без правил шага и округления."""

    value: Decimal

    def __post_init__(self) -> None:
        """Принимает только Decimal, включая ноль, без преобразования float."""
        if (
            not isinstance(self.value, Decimal)
            or not self.value.is_finite()
            or self.value < 0
        ):
            raise InvalidQuantityError(
                "Количество должно быть конечным неотрицательным Decimal."
            )
