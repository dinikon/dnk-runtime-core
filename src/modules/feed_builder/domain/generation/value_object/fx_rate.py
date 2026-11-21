from dataclasses import dataclass
from decimal import Decimal
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.feed_builder.domain.generation.error import InvalidGenerationValueError


@dataclass(frozen=True, slots=True)
class FxRateVO:
    """Хранит точный курс направленной валютной пары без округления MoneyVO."""

    source_currency: CurrencyVO
    target_currency: CurrencyVO
    rate: Decimal

    def __post_init__(self) -> None:
        """Требует разные валюты и конечный положительный Decimal."""
        if (
            not isinstance(self.source_currency, CurrencyVO)
            or not isinstance(self.target_currency, CurrencyVO)
            or self.source_currency == self.target_currency
            or not isinstance(self.rate, Decimal)
            or not self.rate.is_finite()
            or self.rate <= 0
        ):
            raise InvalidGenerationValueError(
                "Нужна валютная пара с положительным курсом."
            )
