from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from src.modules.currency.domain.exchange_rate.error import InvalidExchangeRate
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)


@dataclass(frozen=True, slots=True)
class ExchangeRate:
    """Positive finite per-unit rate for an explicit currency pair."""

    pair: CurrencyPair
    value: Decimal

    def __post_init__(self):
        if (
            not isinstance(self.value, Decimal)
            or not self.value.is_finite()
            or self.value <= 0
        ):
            raise InvalidExchangeRate("Rate must be a positive finite Decimal.")


__all__ = ["ExchangeRate"]
