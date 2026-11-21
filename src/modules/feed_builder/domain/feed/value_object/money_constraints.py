from dataclasses import dataclass
from decimal import Decimal
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.domain.feed.validation import decimal


@dataclass(frozen=True, slots=True)
class MoneyConstraintsVO:
    """Хранит только обязательность и ограничения денежной суммы."""

    required: bool = False
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None

    def __post_init__(self) -> None:
        """Проверяет конечные Decimal и порядок границ без округления."""
        if type(self.required) is not bool:
            raise InvalidFeedValueError("Required должен быть bool.")
        for value in (self.min_amount, self.max_amount):
            if value is not None:
                decimal(value, label="Amount constraint")
        if (
            self.min_amount is not None
            and self.max_amount is not None
            and self.min_amount > self.max_amount
        ):
            raise InvalidFeedValueError(
                "Минимальная сумма не может превышать максимальную."
            )
