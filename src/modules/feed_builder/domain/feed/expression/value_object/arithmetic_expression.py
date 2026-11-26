from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, TYPE_CHECKING
from src.modules.feed_builder.domain.feed.expression.enum.arithmetic_operator import (
    ArithmeticOperator,
)
from src.modules.feed_builder.domain.feed.validation import is_expression
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError

if TYPE_CHECKING:
    from src.modules.feed_builder.domain.feed.types import Expression


@dataclass(frozen=True, slots=True)
class ArithmeticExpressionVO:
    """Описывает бинарную арифметику или NEGATE без исполнения."""

    kind: ClassVar[str] = "arithmetic"
    operator: ArithmeticOperator
    left: Expression | None = None
    right: Expression | None = None
    operand: Expression | None = None

    def __post_init__(self) -> None:
        """Проверяет арность и разрешённые узлы без арифметики над ними."""
        if not isinstance(self.operator, ArithmeticOperator):
            raise InvalidFeedValueError("Нужна типизированная арифметическая операция.")
        if self.operator == ArithmeticOperator.NEGATE:
            valid = (
                is_expression(self.operand) and self.left is None and self.right is None
            )
        else:
            valid = (
                is_expression(self.left)
                and is_expression(self.right)
                and self.operand is None
            )
        if not valid:
            raise InvalidFeedValueError("Операнды не соответствуют арности операции.")
