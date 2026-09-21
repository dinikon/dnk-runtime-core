from __future__ import annotations
from src.modules.currency.domain.directory.error import CurrencyNotFound
from src.modules.currency.domain.enabled_currency.error import CurrencyDisabled
from src.modules.currency.domain.exchange_rate.error import ExchangeRateNotFound
from src.modules.currency.domain.functional_currency.error import (
    FunctionalCurrencyNotConfigured,
)
from src.modules.currency.domain.policy.error import CurrencyPolicyNotConfigured

UNAVAILABLE_CONVERSION = (
    CurrencyNotFound,
    CurrencyDisabled,
    CurrencyPolicyNotConfigured,
    FunctionalCurrencyNotConfigured,
    ExchangeRateNotFound,
)


__all__ = ["UNAVAILABLE_CONVERSION"]
