from datetime import timedelta

from src.modules.currency.application.provider import ProviderCapabilities
from src.modules.currency.domain.models import ProviderCode, CurrencyCodeVO
from .mapper import map_rates


class NbuAdapter:
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
