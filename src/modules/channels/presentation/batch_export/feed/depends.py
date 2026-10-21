from contextlib import AsyncExitStack
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID
from fastapi import Depends, Query, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.modules.channels.presentation.batch_export.assembly import (
    get_export_feed_links,
)
from src.modules.channels.presentation.jobs.scope import tenant_scope
from src.modules.channels.domain.error import ChannelsError
from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.tenancy.application.tenant.tenant_admission import TenantUnavailable
from src.modules.tenancy.infrastructure.tenant_domain.public_hosts import (
    SqlAlchemyTenantPublicHosts,
)
from src.modules.shared.presentation.http.host import extract_request_host
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExportFeedContext:
    """Удерживает admission подписанного tenant до закрытия streaming response."""

    tenant_id: UUID
    sessions: async_sessionmaker[AsyncSession]
    streams: AsyncExitStack


async def get_export_feed_context(
    request: Request, run_id: UUID, access: str = Query(min_length=50, max_length=200)
) -> AsyncIterator[ExportFeedContext]:
    """Проверяет signature до выбора tenant и удерживает admission всего ответа."""
    try:
        tenant_id = get_export_feed_links().authorize(run_id, access, UtcClock().now())
        sessions = getattr(request.app.state, "db", db_helper.session_factory)
        async with sessions() as session:
            if not await SqlAlchemyTenantPublicHosts(session).owns_host(
                tenant_id, extract_request_host(request)
            ):
                raise HTTPException(404, "export_feed_not_found")
        async with tenant_scope(sessions, tenant_id) as connection:
            async with AsyncExitStack() as streams:
                yield ExportFeedContext(
                    tenant_id,
                    async_sessionmaker(connection, expire_on_commit=False),
                    streams,
                )
    except (ChannelsError, TenantUnavailable):
        raise HTTPException(404, "export_feed_not_found") from None


ExportFeedContextDep = Annotated[ExportFeedContext, Depends(get_export_feed_context)]
