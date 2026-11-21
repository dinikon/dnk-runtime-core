from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.feed_builder.domain.feed.validation import decimal
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class MoneyLiteralVO:
    """Хранит денежную константу до финального округления shared MoneyVO."""

    kind: ClassVar[str] = "money"
    amount: Decimal
    currency: CurrencyVO

    def __post_init__(self) -> None:
        """Проверяет точную сумму и валюту, сохраняя все входные разряды."""
        decimal(self.amount, label="Money literal")
        if not isinstance(self.currency, CurrencyVO):
            raise InvalidFeedValueError("Денежный литерал требует CurrencyVO.")
