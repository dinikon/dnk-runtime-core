from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from src.modules.currency.domain.exchange_rate.error import InvalidExchangeRate
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.exchange_rate.value_object.exchange_rate import (
    ExchangeRate,
)
from src.modules.currency.domain.exchange_rate.value_object.rate_derivation import (
    RateDerivation,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class RateQuote:
    """Resolved local rate with dates, derivation and all contributing revisions."""

    pair: CurrencyPair
    rate: Decimal
    requested_date: date
    effective_date: date
    provider_code: ProviderCode
    derivation: RateDerivation
    source_rate_ids: tuple[EntityIdVO, ...] = ()
    bridge_currency: CurrencyCodeVO | None = None

    def __post_init__(self):
        ExchangeRate(self.pair, self.rate)
        if self.effective_date > self.requested_date:
            raise InvalidExchangeRate("A quote cannot use a future rate.")


__all__ = ["RateQuote"]
