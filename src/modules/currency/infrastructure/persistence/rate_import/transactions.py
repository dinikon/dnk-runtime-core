from contextlib import asynccontextmanager
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import Sequence
from src.modules.currency.application.provider.dto.provider_rate_dto import (
    ProviderRateDTO,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.domain.rate_import.value_object.id import RateImportIdVO
from src.modules.currency.infrastructure.persistence.provider_rate.writer import (
    GlobalProviderRateWriter,
)
from src.modules.currency.infrastructure.persistence.rate_import.repository import (
    SqlRateImportRepository,
)
from src.modules.shared.infrastructure.persistence.unit_of_work import UnitOfWork


class ProviderImportUnit:
    """Compose audit and rate repositories over one global transaction."""

    def __init__(self, session: AsyncSession):
        self.imports = SqlRateImportRepository(session)
        self.rates = GlobalProviderRateWriter(session)

    async def start(
        self,
        identifier: RateImportIdVO,
        provider: ProviderCode,
        start_date: date,
        end_date: date,
        now: datetime,
    ) -> None:
        await self.imports.start(identifier, provider, start_date, end_date, now)

    async def finish(
        self,
        identifier: RateImportIdVO,
        *,
        status: str,
        now: datetime,
        received: int = 0,
        created: int = 0,
        updated: int = 0,
        error: str | None = None,
    ) -> None:
        await self.imports.finish(
            identifier,
            status=status,
            now=now,
            received=received,
            created=created,
            updated=updated,
            error=error,
        )

    async def save_many(
        self, *, provider: ProviderCode, rates: Sequence[ProviderRateDTO], now: datetime
    ) -> tuple[int, int]:
        return await self.rates.save_many(provider=provider, rates=rates, now=now)


class ProviderImportTransactions:
    """Open independent attempts, publications, and failed-audit units of work."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    @asynccontextmanager
    async def __call__(self):
        async with UnitOfWork(self.session_factory) as uow:
            yield ProviderImportUnit(uow.session)


__all__ = ["ProviderImportTransactions"]
