from decimal import Decimal
import asyncio
import httpx
import json
from src.modules.currency.domain.provider.error import ProviderRateInvalid
from src.modules.currency.domain.provider.error import ProviderUnavailable


class NbuClient:
    """Fetch bounded NBU responses with transient-error retries."""

    def __init__(self, settings, *, transport=None):
        self.settings, self.transport = settings, transport

    async def fetch(self, *, start_date, end_date):
        params = {
            "start": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
            "sort": "exchangedate",
            "order": "asc",
            "json": "",
        }
        async with httpx.AsyncClient(
            timeout=self.settings.timeout_seconds,
            transport=self.transport,
            follow_redirects=False,
        ) as client:
            for attempt in range(self.settings.retry_count + 1):
                try:
                    response = await client.get(
                        str(self.settings.api_url), params=params
                    )
                    response.raise_for_status()
                    try:
                        value = json.loads(response.text, parse_float=Decimal)
                    except (ValueError, TypeError):
                        raise ProviderRateInvalid(
                            "NBU response is not valid JSON."
                        ) from None
                    if not isinstance(value, list):
                        raise ProviderRateInvalid("NBU response must be an array.")
                    return value
                except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                    retryable = (
                        not isinstance(exc, httpx.HTTPStatusError)
                        or exc.response.status_code == 429
                        or exc.response.status_code >= 500
                    )
                    if not retryable or attempt == self.settings.retry_count:
                        raise ProviderUnavailable("NBU could not be reached.") from exc
                    await asyncio.sleep(min(2**attempt, 8))


__all__ = ["NbuClient"]
