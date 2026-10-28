"""Сборка сценариев синхронизации на существующем внешнем UoW."""

from typing import Annotated
from uuid import uuid4

from fastapi import Depends

from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
)
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.depends import (
    tenant_id_from_context,
    utc_now,
    get_platforms,
)
from src.modules.channels.application.sync_run.service import SyncRuns
from src.modules.channels.application.sync_run.command.start_sync_run.handler import (
    StartSyncRunHandler,
)
from src.modules.channels.application.sync_run.query.get_sync_run.handler import (
    GetSyncRunHandler,
)
from src.modules.channels.application.sync_run.query.get_latest_sync_run.handler import (
    GetLatestSyncRunHandler,
)
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.infrastructure.sync_run.persistence.repository import (
    SqlAlchemySyncRunRepository,
)
from src.modules.channels.infrastructure.sync_run.persistence.query_repository import (
    SqlAlchemySyncRunQueryRepository,
)
from src.modules.channels.infrastructure.sync_run.jobs import SharedPublicationSyncJobs
from src.modules.channels.infrastructure.external_publication.persistence.query_repository import (
    SqlAlchemyPublicationQueryRepository,
)


def get_sync_runs_service(uow: UoWDep) -> SyncRuns:
    """Собирает координацию старта и отмены на той же транзакции."""
    return SyncRuns(
        SqlAlchemySyncRunRepository(uow.session),
        SharedPublicationSyncJobs(build_scheduled_job_repository(uow.session)),
        utc_now,
        uuid4,
    )


SyncRunsDep = Annotated[SyncRuns, Depends(get_sync_runs_service)]


def get_start_sync_run_handler(
    uow: UoWDep, context: AuthenticatedRequestContextDep, runs: SyncRunsDep
) -> StartSyncRunHandler:
    """Собирает ручной запуск с блокировкой корня Channel."""
    return StartSyncRunHandler(
        SqlAlchemyChannelRepository(uow.session, tenant_id_from_context(context)),
        runs,
        get_platforms(),
    )


StartSyncRunHandlerDep = Annotated[
    StartSyncRunHandler, Depends(get_start_sync_run_handler)
]


def get_get_sync_run_handler(uow: UoWDep) -> GetSyncRunHandler:
    """Собирает чтение одного запуска."""
    return GetSyncRunHandler(
        SqlAlchemySyncRunQueryRepository(uow.session),
        SqlAlchemyPublicationQueryRepository(uow.session),
        SharedPublicationSyncJobs(build_scheduled_job_repository(uow.session)),
    )


GetSyncRunHandlerDep = Annotated[GetSyncRunHandler, Depends(get_get_sync_run_handler)]


def get_get_latest_sync_run_handler(uow: UoWDep) -> GetLatestSyncRunHandler:
    """Собирает чтение последнего запуска."""
    return GetLatestSyncRunHandler(
        SqlAlchemySyncRunQueryRepository(uow.session),
        SqlAlchemyPublicationQueryRepository(uow.session),
        SharedPublicationSyncJobs(build_scheduled_job_repository(uow.session)),
    )


GetLatestSyncRunHandlerDep = Annotated[
    GetLatestSyncRunHandler, Depends(get_get_latest_sync_run_handler)
]
