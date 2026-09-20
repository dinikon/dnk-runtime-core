from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol, Sequence
from uuid import uuid4
import asyncio

from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.currency.domain.models import (
    CurrencyPair,
    CurrencyCodeVO,
    ProviderCode,
    ExchangeRate,
)
from src.modules.currency.domain.errors import ProviderUnavailable, ProviderRateInvalid


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    historical_rates: bool
    supported_currencies: bool
    base_currency: CurrencyCodeVO | None
    bulk_download: bool


@dataclass(frozen=True, slots=True)
class ProviderRateDTO:
    pair: CurrencyPair
    rate: Decimal
    effective_date: date
    calculated_date: date | None = None
    published_at: datetime | None = None

    def __post_init__(self):
        ExchangeRate(self.pair, self.rate)


class ExchangeRateProviderPort(Protocol):
    code: ProviderCode
    capabilities: ProviderCapabilities

    async def fetch(
        self, *, start_date: date, end_date: date
    ) -> Sequence[ProviderRateDTO]: ...


class ExchangeRateProviderRegistry:
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


class SyncProviderRates:
    """Durable attempt, atomic publication, independent failure finalization."""

    def __init__(
        self, registry: ExchangeRateProviderRegistry, transactions, clock: ClockPort
    ):
        self.registry, self.transactions, self.clock = registry, transactions, clock

    async def __call__(
        self, *, provider: ProviderCode, start_date: date, end_date: date
    ):
        if end_date < start_date or (end_date - start_date).days > 366:
            raise ProviderRateInvalid("An import range must span at most 367 days.")
        adapter = self.registry.get(provider)
        import_id = uuid4()
        async with self.transactions() as tx:
            await tx.start(import_id, provider, start_date, end_date, self.clock.now())
        received = 0
        try:
            rates = await adapter.fetch(start_date=start_date, end_date=end_date)
            received = len(rates)
            if not rates:
                raise ProviderRateInvalid(
                    "Provider returned no rates for the requested interval."
                )
            async with self.transactions() as tx:
                created, updated = await tx.save_many(
                    provider=provider, rates=rates, now=self.clock.now()
                )
                await tx.finish(
                    import_id,
                    status="succeeded",
                    now=self.clock.now(),
                    received=received,
                    created=created,
                    updated=updated,
                )
            return {
                "id": import_id,
                "status": "succeeded",
                "received_count": received,
                "created_count": created,
                "updated_count": updated,
            }
        except (Exception, asyncio.CancelledError) as exc:
            # This transaction is deliberately outside the rolled-back publication.
            async with self.transactions() as tx:
                await tx.finish(
                    import_id,
                    status="failed",
                    now=self.clock.now(),
                    received=received,
                    error=f"{type(exc).__name__}: import failed",
                )
            raise
