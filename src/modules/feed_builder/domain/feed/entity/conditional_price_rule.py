from __future__ import annotations
from dataclasses import dataclass
from typing import Self, TYPE_CHECKING
from src.modules.feed_builder.domain.feed.value_object.price_rule_id import (
    PriceRuleIdVO,
)
from src.modules.feed_builder.domain.feed.validation import is_condition, is_expression
from src.modules.feed_builder.domain.feed.error import (
    InvalidPriceCalculationDefinitionError,
)

if TYPE_CHECKING:
    from src.modules.feed_builder.domain.feed.types import Condition, Expression


@dataclass(frozen=True, slots=True)
class ConditionalPriceRule:
    """Зависимое правило Feed с устойчивой идентичностью и неизменяемым определением."""

    id: PriceRuleIdVO
    condition: Condition
    expression: Expression

    @classmethod
    def create(
        cls, *, identifier: PriceRuleIdVO, condition: Condition, expression: Expression
    ) -> Self:
        """Создаёт правило с явно переданным ID без выбора ветви или расчёта."""
        return cls.restore(
            identifier=identifier, condition=condition, expression=expression
        )

    @classmethod
    def restore(
        cls, *, identifier: PriceRuleIdVO, condition: Condition, expression: Expression
    ) -> Self:
        """Восстанавливает идентичность и структуру без генерации новых данных."""
        if (
            not isinstance(identifier, PriceRuleIdVO)
            or not is_condition(condition)
            or not is_expression(expression)
        ):
            raise InvalidPriceCalculationDefinitionError(
                "Нужны PriceRuleIdVO, условие и выражение правила."
            )
        return cls(identifier, condition, expression)
