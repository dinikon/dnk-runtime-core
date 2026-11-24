from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.modules.feed_builder.domain.feed.error import InvalidFieldDefinitionError
from src.modules.feed_builder.domain.feed.policy.calculation_semantics import (
    PriceCalculationSemanticPolicy,
)
from src.modules.feed_builder.domain.feed.policy.price_calculation_structure import (
    PriceCalculationStructurePolicy,
)

if TYPE_CHECKING:
    from src.modules.feed_builder.domain.feed.types import Condition


@dataclass(frozen=True, slots=True)
class BooleanCalculationVO:
    """Возвращает логическое значение выбранной ветви IF."""

    condition: Condition
    then_value: bool = True
    else_value: bool = False

    def __post_init__(self) -> None:
        """Проверяет тип ветвей, бюджет и типы исходных условий."""
        if type(self.then_value) is not bool or type(self.else_value) is not bool:
            raise InvalidFieldDefinitionError(
                "Ветви THEN и ELSE требуют true или false."
            )
        PriceCalculationStructurePolicy.validate_nodes(
            [(self.condition, 1, ("condition",))]
        )
        PriceCalculationSemanticPolicy.ensure_condition(self.condition)
