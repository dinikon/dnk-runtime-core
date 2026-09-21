from __future__ import annotations
import asyncio
from src.modules.currency.application.provider.command.sync_provider_rates_command import (
    SyncProviderRatesCommand,
)
from src.modules.currency.application.provider.dto.import_result_dto import (
    ImportResultDTO,
)
from src.modules.currency.application.provider.import_ports import (
    ProviderImportTransactionFactory,
)
from src.modules.currency.application.provider.registry import (
    ExchangeRateProviderRegistry,
)
from src.modules.currency.domain.provider.error import ProviderRateInvalid
from src.modules.shared.domain.time.clock_port import ClockPort


class SyncProviderRates:
    """Durable attempt, atomic publication, independent failure finalization."""

    def __init__(
        self,
        registry: ExchangeRateProviderRegistry,
        transactions: ProviderImportTransactionFactory,
        clock: ClockPort,
    ):
        self.registry, self.transactions, self.clock = registry, transactions, clock

    async def __call__(self, command: SyncProviderRatesCommand) -> ImportResultDTO:
        provider, start_date, end_date = (
            command.provider,
            command.start_date,
            command.end_date,
        )
        if end_date < start_date or (end_date - start_date).days > 366:
            raise ProviderRateInvalid("An import range must span at most 367 days.")
        adapter = self.registry.get(provider)
        import_id = command.id
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
            return ImportResultDTO(command.id, "succeeded", received, created, updated)
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


__all__ = ["SyncProviderRates"]
