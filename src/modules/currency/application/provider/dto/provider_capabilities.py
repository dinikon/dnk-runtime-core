from __future__ import annotations
from dataclasses import dataclass
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Features offered by a registered exchange-rate adapter."""

    historical_rates: bool
    supported_currencies: bool
    base_currency: CurrencyCodeVO | None
    bulk_download: bool


__all__ = ["ProviderCapabilities"]
