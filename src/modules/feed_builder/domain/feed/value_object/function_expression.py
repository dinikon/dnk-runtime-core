from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, TYPE_CHECKING
from src.modules.feed_builder.domain.feed.enum.price_function import PriceFunction
from src.modules.feed_builder.domain.feed.validation import sequence, is_expression
from src.modules.feed_builder.domain.feed.limits import MAX_AST_NODES
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError

if TYPE_CHECKING:
    from src.modules.feed_builder.domain.feed.types import Expression


@dataclass(frozen=True, slots=True)
class FunctionExpressionVO:
    """Описывает вызов разрешённой функции над выражениями."""

    kind: ClassVar[str] = "function"
    function: PriceFunction
    arguments: tuple[Expression, ...]

    def __post_init__(self) -> None:
        """Проверяет арность функции и замораживает её аргументы."""
        arguments = sequence(
            self.arguments, label="Function arguments", maximum=MAX_AST_NODES
        )
        if not isinstance(self.function, PriceFunction) or not all(
            is_expression(value) for value in arguments
        ):
            raise InvalidFeedValueError(
                "Нужны разрешённая функция и выражения аргументов."
            )
        if (self.function == PriceFunction.ABS and len(arguments) != 1) or (
            self.function != PriceFunction.ABS and len(arguments) < 2
        ):
            raise InvalidFeedValueError(
                "ABS требует один аргумент, MIN/MAX — минимум два."
            )
        object.__setattr__(self, "arguments", arguments)
