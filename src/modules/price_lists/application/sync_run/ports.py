from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from pathlib import Path
from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.sync_run.value_object import SyncRunIdVO
from src.modules.price_lists.domain.price_list.repository import PriceListRepository
from src.modules.price_lists.domain.offer.repository import OfferRepository
from src.modules.price_lists.domain.sync_run.repository import SyncRunRepository
from src.modules.price_lists.application.sync_run.dto.parsed_row_dto import ParsedRow
from src.modules.price_lists.application.sync_run.dto.source_dto import (
    FetchResult,
    SourceInspection,
)


class SourceFetcher(Protocol):
    """Порт загрузки и удаления временного источника."""

    def open(self, url: str) -> AbstractAsyncContextManager[FetchResult]: ...


class SourceParserPort(Protocol):
    """Порт ограниченного async-разбора файла."""

    def batches(
        self,
        path: Path,
        source_format: str,
        source_config: dict,
        mapping: dict,
        *,
        limit: int | None = None,
    ) -> AsyncIterator[list[ParsedRow]]: ...
    async def inspect_source(
        self, path: Path, source_format: str, source_config: dict
    ) -> SourceInspection: ...


class SourceCipher(Protocol):
    """Порт преобразования секретного URL."""

    def encrypt(self, value: str) -> str: ...
    def decrypt(self, value: str) -> str: ...


class CalendarPort(Protocol):
    """Порт расчёта CRON в заданной timezone."""

    def occurrences(
        self, expression: str, timezone: str, *, after: datetime, count: int = 5
    ) -> list[datetime]: ...
    def next(self, expression: str, timezone: str, *, after: datetime) -> datetime: ...


class IdentifierPort(Protocol):
    """Генератор новых доменных идентификаторов."""

    def new(self) -> EntityIdVO: ...


class JobSchedulerPort(Protocol):
    """Планирование и fencing задач модуля."""

    async def schedule_sync(
        self,
        tenant_id: EntityIdVO,
        price_list_id: PriceListIdVO,
        revision: int,
        run_at: datetime,
        trigger: str,
        *,
        job_id: EntityIdVO | None = None,
    ) -> EntityIdVO: ...
    async def schedule_cleanup(
        self, tenant_id: EntityIdVO, run_at: datetime
    ) -> None: ...
    async def cancel(
        self,
        tenant_id: EntityIdVO,
        price_list_id: PriceListIdVO,
        now: datetime,
        *,
        delete: bool = False,
    ) -> int: ...
    async def require_lease(
        self,
        tenant_id: EntityIdVO,
        job_id: EntityIdVO,
        token: str,
        *,
        fence: bool = False,
    ) -> None: ...


class StagingPort(Protocol):
    """Пакетное staging-хранилище, невидимое читателям предложений."""

    async def append(
        self, tenant_id: EntityIdVO, run_id: SyncRunIdVO, rows: list[ParsedRow]
    ) -> None: ...
    async def read_batch(
        self, tenant_id: EntityIdVO, run_id: SyncRunIdVO, after: int, limit: int
    ) -> list[ParsedRow]: ...
    async def quarantine(
        self, tenant_id: EntityIdVO, run_id: SyncRunIdVO, external_ids: list[str]
    ) -> None: ...
    async def delete_batch(
        self,
        tenant_id: EntityIdVO,
        run_id: SyncRunIdVO,
        *,
        keep_quarantine: bool = False,
    ) -> int: ...
    async def cleanup_batch(
        self, tenant_id: EntityIdVO, older_than: datetime
    ) -> int: ...


class ImportTransaction(Protocol):
    """UoW без SQLAlchemy в application-контракте."""

    prices: PriceListRepository
    offers: OfferRepository
    runs: SyncRunRepository
    staging: StagingPort
    jobs: JobSchedulerPort

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class ImportTransactionFactory(Protocol):
    """Фабрика независимых коротких UoW фоновой задачи."""

    def __call__(self) -> AbstractAsyncContextManager[ImportTransaction]: ...


class PriceListLock(Protocol):
    """Межрепличная блокировка одного tenant/price-list."""

    def hold(
        self, tenant_id: EntityIdVO, price_list_id: PriceListIdVO
    ) -> AbstractAsyncContextManager[bool]: ...


class ImportObserver(Protocol):
    """Порт эксплуатационных метрик без зависимости application от Prometheus."""

    def phase(self, name: str, source_format: str, seconds: float) -> None: ...
    def completed(
        self,
        source_format: str,
        trigger: str,
        status: str,
        counters: dict[str, int],
        seconds: float,
    ) -> None: ...
    def downloaded(self, source_format: str, size: int) -> None: ...


__all__ = [
    "SourceFetcher",
    "SourceParserPort",
    "SourceCipher",
    "CalendarPort",
    "IdentifierPort",
    "JobSchedulerPort",
    "StagingPort",
    "ImportTransaction",
    "ImportTransactionFactory",
    "PriceListLock",
    "ImportObserver",
]
