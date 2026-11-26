from src.modules.feed_builder.application.export_state.query.download_public_feed.handler import (
    DownloadPublicFeedHandler,
)
from src.modules.feed_builder.application.export_state.query.get_feed_export_state.handler import (
    GetFeedExportStateHandler,
)
from src.modules.feed_builder.application.export_state.query.list_latest_feed_export_issues.handler import (
    ListLatestFeedExportIssuesHandler,
)
from src.modules.feed_builder.infrastructure.export_state.files import (
    FilesFeedExportContent,
)
from src.modules.files.infrastructure.assembly import build_files_handlers
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack

from typing import Annotated

from fastapi import Depends

from src.modules.feed_builder.application.export_state.command.request_feed_refresh.handler import (
    RequestFeedRefreshHandler,
)
from src.modules.feed_builder.application.export_state.command.rotate_feed_public_link.handler import (
    RotateFeedPublicLinkHandler,
)
from src.modules.feed_builder.application.export_state.port.query_repository import (
    FeedExportQueryRepositoryProtocol,
)
from src.modules.feed_builder.infrastructure.export_state.persistence.query_repository import (
    SqlAlchemyFeedExportQueryRepository,
)
from src.modules.feed_builder.infrastructure.export_state.persistence.repository import (
    SqlAlchemyFeedExportStateRepository,
)
from src.modules.feed_builder.infrastructure.export_state.tenancy import (
    TenancyPublicFeedTenantResolver,
)
from src.modules.feed_builder.presentation.feed.depends import FeedRepositoryDep, FeedSettingsRepositoryDep
from src.modules.shared.presentation.jobs.management import (
    build_schedule_scheduled_job_use_case,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.tenancy.presentation.depends.application import (
    ResolveReadableTenantByHostHandlerDep,
    TenantSchemaNamingDep,
)


def get_feed_export_queries(uow: UoWDep) -> FeedExportQueryRepositoryProtocol:
    """Собирает чтение экспорта на tenant-сессии."""
    return SqlAlchemyFeedExportQueryRepository(uow.session)


def get_request_feed_refresh_handler(
    uow: UoWDep,
    feeds: FeedRepositoryDep,
    clock: ClockDep,
    ids: UuidDep,
) -> RequestFeedRefreshHandler:
    """Подключает постановку очереди к UoW сохранения задачи."""
    return RequestFeedRefreshHandler(
        feeds,
        SqlAlchemyFeedExportStateRepository(uow.session),
        build_schedule_scheduled_job_use_case(
            session=uow.session, clock=clock, uuid_generator=ids
        ),
        clock,
        ids,
    )


def get_rotate_feed_public_link_handler(
    uow: UoWDep,
    feeds: FeedSettingsRepositoryDep,
    clock: ClockDep,
    ids: UuidDep,
) -> RotateFeedPublicLinkHandler:
    """Собирает смену адреса на общей tenant-сессии."""
    return RotateFeedPublicLinkHandler(
        feeds, SqlAlchemyFeedExportQueryRepository(uow.session), clock, ids
    )


FeedExportQueriesDep = Annotated[
    FeedExportQueryRepositoryProtocol, Depends(get_feed_export_queries)
]
RequestFeedRefreshHandlerDep = Annotated[
    RequestFeedRefreshHandler, Depends(get_request_feed_refresh_handler)
]
RotateFeedPublicLinkHandlerDep = Annotated[
    RotateFeedPublicLinkHandler, Depends(get_rotate_feed_public_link_handler)
]


def get_download_public_feed_handler(
    uow: UoWDep,
    queries: FeedExportQueriesDep,
    resolve_tenant: ResolveReadableTenantByHostHandlerDep,
    tenant_naming: TenantSchemaNamingDep,
) -> DownloadPublicFeedHandler:
    """Подключает Tenancy и Files на той же сессии, что и запрос фида."""
    return DownloadPublicFeedHandler(
        TenancyPublicFeedTenantResolver(resolve_tenant, uow.session, tenant_naming),
        queries,
        FilesFeedExportContent(build_files_handlers(uow.session).content),
    )


def get_export_state_handler(
    queries: FeedExportQueriesDep,
) -> GetFeedExportStateHandler:
    """Собирает чтение текущего состояния."""
    return GetFeedExportStateHandler(queries)


def get_latest_export_issues_handler(
    queries: FeedExportQueriesDep,
) -> ListLatestFeedExportIssuesHandler:
    """Собирает ограниченное чтение диагностик."""
    return ListLatestFeedExportIssuesHandler(queries)


async def get_public_feed_streams() -> AsyncIterator[AsyncExitStack]:
    """Удерживает и освобождает потоки при завершении ASGI-запроса."""
    async with AsyncExitStack() as streams:
        yield streams


DownloadPublicFeedHandlerDep = Annotated[
    DownloadPublicFeedHandler, Depends(get_download_public_feed_handler)
]
GetFeedExportStateHandlerDep = Annotated[
    GetFeedExportStateHandler, Depends(get_export_state_handler)
]
ListLatestFeedExportIssuesHandlerDep = Annotated[
    ListLatestFeedExportIssuesHandler, Depends(get_latest_export_issues_handler)
]
PublicFeedStreamsDep = Annotated[AsyncExitStack, Depends(get_public_feed_streams)]
