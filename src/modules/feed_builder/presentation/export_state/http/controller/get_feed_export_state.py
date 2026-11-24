from dataclasses import asdict
from uuid import UUID

from src.modules.feed_builder.application.export_state.query.get_feed_export_state.query import (
    GetFeedExportStateQuery,
)

from fastapi import HTTPException, Request

from src.modules.feed_builder.presentation.export_state.depends import (
    GetFeedExportStateHandlerDep,
)
from src.modules.feed_builder.presentation.export_state.http.response.get_feed_export_state import (
    ActiveFileResponse,
    ExportReportResponse,
    ExportTaskResponse,
    GetFeedExportStateResponse,
)
from src.modules.feed_builder.presentation.export_state.http.urls import public_feed_url
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def get_feed_export_state(
    feed_id: UUID,
    request: Request,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: GetFeedExportStateHandlerDep,
) -> GetFeedExportStateResponse:
    """Возвращает сводку экспорта без исходных данных Catalog."""
    await require_feed_access(
        context, authorization, action="feed_builder.feed.read", feed_id=feed_id
    )
    result = await handler.execute(GetFeedExportStateQuery(feed_id))
    if result is None:
        raise HTTPException(404, "Feed не найден.")
    principal = context.principal
    assert principal is not None and principal.tenant_id is not None
    editable = await authorization.can(
        user_id=UUID(principal.user_id),
        tenant_id=UUID(principal.tenant_id),
        action="feed_builder.feed.update",
        resource_type="feed_builder.feed",
        resource_id=feed_id,
    )
    active = result.active
    return GetFeedExportStateResponse(
        feed_version=result.feed_version,
        can_refresh=editable and result.can_refresh,
        can_rotate=editable and result.can_rotate,
        task=ExportTaskResponse(**asdict(result.task)) if result.task else None,
        report=ExportReportResponse(**asdict(result.report)) if result.report else None,
        active=(
            ActiveFileResponse(
                url=public_feed_url(request, active.public_link_id, active.format),
                format=active.format,
                as_of=active.as_of,
                published_at=active.published_at,
            )
            if active
            else None
        ),
    )
