from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, TYPE_CHECKING
from src.modules.feed_builder.domain.feed.enum.comparison_operator import (
    ComparisonOperator,
)
from src.modules.feed_builder.domain.feed.validation import is_condition_operand
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError

if TYPE_CHECKING:
    from src.modules.feed_builder.domain.feed.types import ConditionOperand


@dataclass(frozen=True, slots=True)
class ComparisonConditionVO:
    """Описывает сравнение параметров/литералов без выбора ветви."""

    kind: ClassVar[str] = "comparison"
    operator: ComparisonOperator
    left: ConditionOperand
    right: ConditionOperand

    def __post_init__(self) -> None:
        """Проверяет оператор и формы операндов; семантические типы проверят позже."""
        if (
            not isinstance(self.operator, ComparisonOperator)
            or not is_condition_operand(self.left)
            or not is_condition_operand(self.right)
        ):
            raise InvalidFeedValueError("Нужны типизированные сравнение и операнды.")
