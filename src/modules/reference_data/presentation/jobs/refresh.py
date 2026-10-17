from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from uuid import NAMESPACE_URL, uuid5

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.reference_data.application.country.command.sync_countries.command import (
    SyncCountriesCommand,
)
from src.modules.reference_data.application.country.command.sync_countries.handler import (
    SyncCountriesHandler,
)
from src.modules.reference_data.application.currency.command.sync_currencies.command import (
    SyncCurrenciesCommand,
)
from src.modules.reference_data.application.currency.command.sync_currencies.handler import (
    SyncCurrenciesHandler,
)
from src.modules.reference_data.application.locale.command.sync_locales.command import (
    SyncLocalesCommand,
)
from src.modules.reference_data.application.locale.command.sync_locales.handler import (
    SyncLocalesHandler,
)
from src.modules.reference_data.application.time_zone.command.sync_time_zones.command import (
    SyncTimeZonesCommand,
)
from src.modules.reference_data.application.time_zone.command.sync_time_zones.handler import (
    SyncTimeZonesHandler,
)
from src.modules.reference_data.infrastructure.persistence.models.sync_state import (
    ReferenceSyncStateModel,
)
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.reference_data.infrastructure.observability.metrics import (
    reference_data_last_success_timestamp,
    reference_data_sync_total,
)
from src.modules.reference_data.infrastructure.source.cldr import CldrClient
from src.modules.reference_data.infrastructure.country.source import CldrCountrySource
from src.modules.reference_data.infrastructure.locale.source import CldrLocaleSource
from src.modules.reference_data.infrastructure.time_zone.source import (
    IanaTimeZoneSource,
)
from src.modules.reference_data.infrastructure.currency.source import SixCurrencySource
from src.modules.shared.application.jobs.schedule_scheduled_job_command import (
    ScheduleScheduledJobCommand,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.presentation.jobs.management import (
    build_schedule_scheduled_job_use_case,
)

DATASETS = ("countries", "currencies", "locales", "time-zones")
JOB_TYPE = "reference_data.refresh"
_SCENARIOS = {
    "countries": (SyncCountriesHandler, SyncCountriesCommand),
    "currencies": (SyncCurrenciesHandler, SyncCurrenciesCommand),
    "locales": (SyncLocalesHandler, SyncLocalesCommand),
    "time-zones": (SyncTimeZonesHandler, SyncTimeZonesCommand),
}


def _source_for(dataset: str, client: httpx.AsyncClient):
    cldr = CldrClient(client)
    return {
        "countries": CldrCountrySource(cldr),
        "currencies": SixCurrencySource(client),
        "locales": CldrLocaleSource(cldr),
        "time-zones": IanaTimeZoneSource(client),
    }[dataset]


async def sync_dataset(
    dataset: str, session_factory: async_sessionmaker[AsyncSession]
) -> tuple[str, int, datetime]:
    if dataset not in DATASETS:
        raise ValueError(f"Unknown reference dataset: {dataset}")
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            source = _source_for(dataset, client)
            async with UnitOfWork(session_factory) as uow:
                handler_type, command_type = _SCENARIOS[dataset]
                result = await handler_type(
                    source, SqlAlchemyCatalogRepository(uow.session), UtcClock()
                ).execute(command_type())
    except Exception:
        reference_data_sync_total.labels(dataset=dataset, result="failed").inc()
        raise
    reference_data_sync_total.labels(dataset=dataset, result="success").inc()
    reference_data_last_success_timestamp.labels(dataset=dataset).set(
        result[2].timestamp()
    )
    return result


class ReferenceDataRefreshJobHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(self, job: ScheduledJob) -> None:
        if job.tenant_id is not None:
            raise ValueError("Reference refresh must be a global job")
        dataset = job.payload.get("dataset")
        if dataset not in DATASETS:
            raise ValueError("Invalid reference refresh dataset")
        await sync_dataset(dataset, self._session_factory)


def weekly_window(now: datetime) -> datetime:
    """Monday 03:00 UTC, most recently elapsed."""
    utc = now.astimezone(UTC)
    monday = datetime.combine(utc.date() - timedelta(days=utc.weekday()), time(3), UTC)
    return monday if utc >= monday else monday - timedelta(days=7)


async def ensure_weekly_jobs(
    session_factory: async_sessionmaker[AsyncSession], now: datetime
) -> None:
    """Idempotently enqueues this week's missing global refreshes."""
    window = weekly_window(now)
    async with UnitOfWork(session_factory) as uow:
        scheduler = build_schedule_scheduled_job_use_case(session=uow.session)
        latest = dict(
            (
                await uow.session.execute(
                    select(
                        ReferenceSyncStateModel.dataset,
                        ReferenceSyncStateModel.last_success_at,
                    )
                )
            ).all()
        )
        for dataset in DATASETS:
            if latest.get(dataset) is not None and latest[dataset] >= window:
                continue
            await scheduler(
                ScheduleScheduledJobCommand(
                    tenant_id=None,
                    job_type=JOB_TYPE,
                    payload={"dataset": dataset},
                    run_at=window,
                    job_id=uuid5(
                        NAMESPACE_URL, f"reference-data:{dataset}:{window.isoformat()}"
                    ),
                )
            )
