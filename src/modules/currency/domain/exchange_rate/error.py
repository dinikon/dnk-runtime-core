from __future__ import annotations
from src.modules.currency.domain.error import CurrencyError


class InvalidExchangeRate(CurrencyError):
    """Rate is not a positive finite Decimal value for its pair."""

    code = "invalid_exchange_rate"


class ExchangeRateNotFound(CurrencyError):
    """Selected source has no eligible local rate for the requested pair and date."""

    code = "exchange_rate_not_found"


class CrossRateUnavailable(ExchangeRateNotFound):
    """No eligible same-source and common-date cross-rate legs exist."""

    code = "cross_rate_unavailable"


__all__ = ["CrossRateUnavailable", "ExchangeRateNotFound", "InvalidExchangeRate"]
