from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from decimal import Decimal
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.exchange_rate.value_object.exchange_rate import (
    ExchangeRate,
)


@dataclass(frozen=True, slots=True)
class ProviderRateDTO:
    """Validated per-unit provider input with effective and calculation dates."""

    pair: CurrencyPair
    rate: Decimal
    effective_date: date
    calculated_date: date | None = None
    published_at: datetime | None = None

    def __post_init__(self):
        ExchangeRate(self.pair, self.rate)


__all__ = ["ProviderRateDTO"]
