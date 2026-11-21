"""Чистые проверки собственных значений без бизнес-оркестрации и I/O."""

from decimal import Decimal
import re

from src.modules.feed_builder.domain.feed.error import (
    DefinitionStructureLimitExceededError,
    InvalidFeedValueError,
)
from src.modules.feed_builder.domain.feed.limits import (
    MAX_LITERAL_DIGITS,
    MAX_LITERAL_EXPONENT,
)


def text(value: str, *, label: str, maximum: int, pattern: str | None = None) -> str:
    """Нормализует непустую строку, ограничивая длину, форму и управляющие символы."""
    if not isinstance(value, str):
        raise InvalidFeedValueError(f"{label}: требуется строка.")
    result = value.strip()
    if not result or len(result) > maximum or not result.isprintable():
        raise InvalidFeedValueError(f"{label}: недопустимая длина или символы.")
    if pattern is not None and re.fullmatch(pattern, result) is None:
        raise InvalidFeedValueError(f"{label}: недопустимый формат.")
    return result


def decimal(value: Decimal, *, label: str) -> None:
    """Проверяет конечный точный Decimal без округления и ambient context."""
    if not isinstance(value, Decimal) or not value.is_finite():
        raise InvalidFeedValueError(f"{label}: требуется конечный Decimal.")
    parts = value.as_tuple()
    if (
        len(parts.digits) > MAX_LITERAL_DIGITS
        or abs(parts.exponent) > MAX_LITERAL_EXPONENT
    ):
        raise InvalidFeedValueError(
            f"{label}: превышена точность или степень литерала."
        )


def sequence[T](
    value: tuple[T, ...] | list[T], *, label: str, maximum: int
) -> tuple[T, ...]:
    """Копирует конечный list/tuple в tuple с проверкой структурного бюджета."""
    if not isinstance(value, (tuple, list)):
        raise InvalidFeedValueError(f"{label}: требуется list или tuple.")
    if len(value) > maximum:
        raise DefinitionStructureLimitExceededError(
            f"{label}: превышен размер состава."
        )
    return tuple(value)


def is_expression(value: object) -> bool:
    """Распознаёт только разрешённые узлы, откладывая импорты рекурсивного графа."""
    from src.modules.feed_builder.domain.feed.value_object.parameter_reference import (
        ParameterReferenceVO,
    )
    from src.modules.feed_builder.domain.feed.value_object.decimal_literal import (
        DecimalLiteralVO,
    )
    from src.modules.feed_builder.domain.feed.value_object.money_literal import (
        MoneyLiteralVO,
    )
    from src.modules.feed_builder.domain.feed.value_object.arithmetic_expression import (
        ArithmeticExpressionVO,
    )
    from src.modules.feed_builder.domain.feed.value_object.function_expression import (
        FunctionExpressionVO,
    )

    return isinstance(
        value,
        (
            ParameterReferenceVO,
            DecimalLiteralVO,
            MoneyLiteralVO,
            ArithmeticExpressionVO,
            FunctionExpressionVO,
        ),
    )


def is_condition_operand(value: object) -> bool:
    """Распознаёт выражение или типизированный литерал сравнения."""
    from src.modules.feed_builder.domain.feed.value_object.scalar_literal import (
        ScalarLiteralVO,
    )
    from src.modules.feed_builder.domain.feed.value_object.collection_literal import (
        CollectionLiteralVO,
    )

    return is_expression(value) or isinstance(
        value, (ScalarLiteralVO, CollectionLiteralVO)
    )


def is_condition(value: object) -> bool:
    """Распознаёт только зарегистрированные структуры условий."""
    from src.modules.feed_builder.domain.feed.value_object.comparison_condition import (
        ComparisonConditionVO,
    )
    from src.modules.feed_builder.domain.feed.value_object.logical_condition import (
        LogicalConditionVO,
    )
    from src.modules.feed_builder.domain.feed.value_object.presence_condition import (
        PresenceConditionVO,
    )

    return isinstance(
        value, (ComparisonConditionVO, LogicalConditionVO, PresenceConditionVO)
    )
