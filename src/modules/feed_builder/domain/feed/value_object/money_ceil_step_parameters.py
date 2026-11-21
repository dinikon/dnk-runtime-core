from dataclasses import dataclass
from decimal import Decimal
from src.modules.feed_builder.domain.feed.validation import decimal
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class MoneyCeilStepParametersVO:
    """Описывает шаг округления денег, сохраняя исходную точность Decimal."""

    step: Decimal

    def __post_init__(self) -> None:
        """Требует положительный конечный шаг без преобразования float."""
        decimal(self.step, label="Rounding step")
        if self.step <= 0:
            raise InvalidFeedValueError("Шаг округления должен быть положительным.")
