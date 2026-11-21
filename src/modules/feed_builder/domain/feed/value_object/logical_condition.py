from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, TYPE_CHECKING
from src.modules.feed_builder.domain.feed.enum.logical_operator import LogicalOperator
from src.modules.feed_builder.domain.feed.validation import is_condition, sequence
from src.modules.feed_builder.domain.feed.limits import MAX_AST_NODES
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError

if TYPE_CHECKING:
    from src.modules.feed_builder.domain.feed.types import Condition


@dataclass(frozen=True, slots=True)
class LogicalConditionVO:
    """Хранит упорядоченную группу ALL/ANY либо единственное условие NOT."""

    kind: ClassVar[str] = "logical"
    operator: LogicalOperator
    operands: tuple[Condition, ...]

    def __post_init__(self) -> None:
        """Проверяет непустой состав и арность NOT без исполнения условий."""
        operands = sequence(
            self.operands, label="Logical operands", maximum=MAX_AST_NODES
        )
        if (
            not isinstance(self.operator, LogicalOperator)
            or not operands
            or not all(is_condition(value) for value in operands)
        ):
            raise InvalidFeedValueError("Нужны логическая операция и непустые условия.")
        if self.operator == LogicalOperator.NOT and len(operands) != 1:
            raise InvalidFeedValueError("NOT требует ровно одно условие.")
        object.__setattr__(self, "operands", operands)
