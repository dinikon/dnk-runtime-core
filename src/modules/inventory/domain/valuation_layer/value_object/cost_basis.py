from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.valuation_layer.error import InvalidCostBasisError
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class CostBasisVO:
    """Фиксирует полную стоимость положительного количества без вычисления округлённой цены единицы."""

    quantity: QuantityVO
    total_cost: MoneyVO

    def __post_init__(self) -> None:
        """Проверяет собственное положительное количество и неотрицательную сумму, включая бесплатное поступление."""
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Требует типизированные конечные величины и сохранённую точность общего MoneyVO."""
        if (
            not isinstance(self.quantity, QuantityVO)
            or not isinstance(self.quantity.value, Decimal)
            or not self.quantity.value.is_finite()
            or self.quantity.value <= 0
            or not isinstance(self.total_cost, MoneyVO)
            or not isinstance(self.total_cost.amount, Decimal)
            or not self.total_cost.amount.is_finite()
            or self.total_cost.amount < 0
        ):
            raise InvalidCostBasisError(
                "Нужны положительный QuantityVO и неотрицательный конечный MoneyVO полной стоимости."
            )
        if MoneyVO(self.total_cost.amount, self.total_cost.currency) != self.total_cost:
            raise InvalidCostBasisError(
                "Стоимость должна соответствовать сохранённой точности MoneyVO."
            )
