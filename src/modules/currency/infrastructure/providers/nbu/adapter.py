from datetime import timedelta
from src.modules.currency.application.provider.dto.provider_capabilities import (
    ProviderCapabilities,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.infrastructure.providers.nbu.mapper import map_rates
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


class NbuAdapter:
    """Normalize NBU payloads to dated per-unit provider rates."""

    code = ProviderCode("NBU")
    capabilities = ProviderCapabilities(True, False, CurrencyCodeVO("UAH"), True)

    def __init__(self, client):
        self.client = client

    async def fetch(self, *, start_date, end_date):
        rates = []
        day = start_date
        while day <= end_date:
            last = min(day + timedelta(days=30), end_date)
            payload = await self.client.fetch(start_date=day, end_date=last)
            rates.extend(map_rates(payload, start_date=day, end_date=last))
            day = last + timedelta(days=1)
        return rates


__all__ = ["NbuAdapter"]
