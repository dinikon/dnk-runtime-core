from dataclasses import dataclass
from decimal import Decimal

from src.modules.feed_builder.domain.feed.validation import decimal


@dataclass(frozen=True, slots=True)
class PriceAmountVO:
    """Хранит точную сумму FeedBuilder без валютной метки и неявного округления."""

    amount: Decimal

    def __post_init__(self) -> None:
        """Требует конечный Decimal в структурном бюджете, сохраняя все разряды."""
        decimal(self.amount, label="Price amount")
