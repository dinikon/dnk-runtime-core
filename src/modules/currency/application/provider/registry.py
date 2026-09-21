from __future__ import annotations
from src.modules.currency.application.provider.ports import ExchangeRateProviderPort
from src.modules.currency.domain.provider.error import ProviderUnavailable
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode


class ExchangeRateProviderRegistry:
    """Registered external providers available in this deployment."""

    def __init__(self):
        self.providers = {}

    def register(self, provider: ExchangeRateProviderPort):
        if provider.code in self.providers:
            raise ValueError(f"Duplicate provider {provider.code}.")
        self.providers[provider.code] = provider

    def get(self, code: ProviderCode) -> ExchangeRateProviderPort:
        if code not in self.providers:
            raise ProviderUnavailable(f"Provider {code} is not registered.")
        return self.providers[code]


__all__ = ["ExchangeRateProviderRegistry"]
