from dataclasses import dataclass
from src.modules.feed_builder.domain.feed.value_object.price_amount import PriceAmountVO
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class PriceValueVO:
    """Объединяет разрешённую сумму и необязательную метку результата без конвертации."""

    amount: PriceAmountVO
    currency: CurrencyVO | None = None

    def __post_init__(self) -> None:
        """Проверяет собственные значения без округления по коду валюты."""
        if not isinstance(self.amount, PriceAmountVO) or (
            self.currency is not None and not isinstance(self.currency, CurrencyVO)
        ):
            raise InvalidFeedValueError(
                "Нужны точная сумма и необязательная валютная метка."
            )
