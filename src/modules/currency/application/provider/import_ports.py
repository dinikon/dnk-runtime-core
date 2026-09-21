from contextlib import AbstractAsyncContextManager
from datetime import datetime, date
from typing import Protocol, Sequence
from src.modules.currency.application.provider.dto.provider_rate_dto import (
    ProviderRateDTO,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.domain.rate_import.value_object.id import RateImportIdVO


class GlobalProviderRateWriter(Protocol):
    """Publish immutable provider revisions with semantic idempotency."""

    async def save_many(
        self, *, provider: ProviderCode, rates: Sequence[ProviderRateDTO], now: datetime
    ) -> tuple[int, int]: ...


class ProviderImportTransaction(GlobalProviderRateWriter, Protocol):
    """Atomic rate publication and its global import audit."""

    async def start(
        self,
        identifier: RateImportIdVO,
        provider: ProviderCode,
        start_date: date,
        end_date: date,
        now: datetime,
    ) -> None: ...
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
    ) -> None: ...


class ProviderImportTransactionFactory(Protocol):
    """Independent global units of work for attempts, publication and failure audit."""

    def __call__(self) -> AbstractAsyncContextManager[ProviderImportTransaction]: ...


__all__ = [
    "GlobalProviderRateWriter",
    "ProviderImportTransaction",
    "ProviderImportTransactionFactory",
]
