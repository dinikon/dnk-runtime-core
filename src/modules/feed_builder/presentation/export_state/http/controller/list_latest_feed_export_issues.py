from typing import Annotated, Literal
from uuid import UUID

from src.modules.feed_builder.application.export_state.query.list_latest_feed_export_issues.query import (
    ListLatestFeedExportIssuesQuery,
)

from fastapi import HTTPException, Query

from src.modules.feed_builder.presentation.export_state.depends import (
    ListLatestFeedExportIssuesHandlerDep,
)
from src.modules.feed_builder.presentation.export_state.http.response.list_latest_feed_export_issues import (
    ExportIssueResponse,
    ListLatestFeedExportIssuesResponse,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def list_latest_feed_export_issues(
    feed_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ListLatestFeedExportIssuesHandlerDep,
    severity: Literal["ERROR", "WARNING"] | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=2147483647)] = 0,
) -> ListLatestFeedExportIssuesResponse:
    """Читает ограниченную страницу последней диагностики."""
    for action in ("feed_builder.feed.read", "feed_builder.publication.read"):
        await require_feed_access(
            context, authorization, action=action, feed_id=feed_id
        )
    result = await handler.execute(
        ListLatestFeedExportIssuesQuery(feed_id, severity, limit, offset)
    )
    if result is None:
        raise HTTPException(404, "Feed не найден.")
    return ListLatestFeedExportIssuesResponse(
        items=tuple(
            ExportIssueResponse.model_validate(issue) for issue in result.items
        ),
        total=result.total,
    )
