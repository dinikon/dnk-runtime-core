from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.error import InvalidConversionFactorError


@dataclass(frozen=True, slots=True)
class ConversionFactorVO:
    """Число базовых единиц в одной дополнительной единице учёта."""

    value: Decimal

    def __post_init__(self) -> None:
        """Принимает только конечный положительный Decimal без преобразования float."""
        if (
            not isinstance(self.value, Decimal)
            or not self.value.is_finite()
            or self.value <= 0
        ):
            raise InvalidConversionFactorError(
                "Коэффициент должен быть конечным положительным Decimal."
            )
