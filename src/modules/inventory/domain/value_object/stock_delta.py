from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.error import InvalidStockDeltaError


@dataclass(frozen=True, slots=True)
class StockDeltaVO:
    """Конечное знаковое изменение количества, включая ноль, без правил проводки."""

    value: Decimal

    def __post_init__(self) -> None:
        """Принимает только конечный Decimal без преобразования и округления."""
        if not isinstance(self.value, Decimal) or not self.value.is_finite():
            raise InvalidStockDeltaError(
                "Изменение количества должно быть конечным Decimal с любым знаком."
            )
