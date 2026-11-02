from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.error import InvalidQuantityRulesError


@dataclass(frozen=True, slots=True)
class QuantityRulesVO:
    """Точный положительный шаг количества от нуля в базовой единице товара."""

    step: Decimal

    def __post_init__(self) -> None:
        """Принимает только конечный положительный Decimal без округления."""
        if (
            not isinstance(self.step, Decimal)
            or not self.step.is_finite()
            or self.step <= 0
        ):
            raise InvalidQuantityRulesError(
                "Шаг количества должен быть конечным положительным Decimal."
            )
