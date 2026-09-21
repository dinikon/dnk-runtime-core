from __future__ import annotations
from src.modules.currency.domain.error import CurrencyError


class ProviderUnavailable(CurrencyError):
    """Provider transport could not complete within its retry budget."""

    code = "provider_unavailable"


class ProviderRateInvalid(CurrencyError):
    """Provider response cannot be atomically published as valid rates."""

    code = "provider_rate_invalid"


class RateSourceNotRegistered(CurrencyError):
    """Requested configuration source is not registered in this deployment."""

    code = "rate_source_not_registered"


__all__ = ["ProviderRateInvalid", "ProviderUnavailable", "RateSourceNotRegistered"]
