from dataclasses import dataclass
from decimal import Decimal

from src.modules.inventory.domain.valuation_layer.error import (
    InvalidValuationIssueAllocationError,
)
from src.modules.inventory.domain.valuation_layer.value_object.identifier import (
    ValuationLayerIdVO,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO


@dataclass(frozen=True, slots=True)
class ValuationLayerIssueAllocationVO:
    """Назначает слою часть ISSUE с фиксацией ожидаемой версии без предварительной оценки стоимости."""

    layer_id: ValuationLayerIdVO
    quantity: QuantityVO
    expected_version: int

    def __post_init__(self) -> None:
        """Проверяет собственные значения назначения при создании VO."""
        self.ensure_valid()

    def ensure_valid(self) -> None:
        """Требует номинальную ссылку, положительное конечное количество и строгую неотрицательную версию."""
        if (
            not isinstance(self.layer_id, ValuationLayerIdVO)
            or not isinstance(self.quantity, QuantityVO)
            or not isinstance(self.quantity.value, Decimal)
            or not self.quantity.value.is_finite()
            or self.quantity.value <= 0
            or type(self.expected_version) is not int
            or self.expected_version < 0
        ):
            raise InvalidValuationIssueAllocationError(
                "Нужны ValuationLayerIdVO, положительный QuantityVO и строгая версия от нуля."
            )
