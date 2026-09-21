from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.exchange_rate.value_object.exchange_rate import (
    ExchangeRate,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class RateRecord:
    """Common immutable provenance of a stored exchange-rate revision."""

    id: EntityIdVO
    pair: CurrencyPair
    rate: Decimal
    effective_date: date
    provider_code: ProviderCode
    revision: int = 1
    is_current: bool = True
    calculated_date: date | None = None

    def __post_init__(self):
        ExchangeRate(self.pair, self.rate)


__all__ = ["RateRecord"]
