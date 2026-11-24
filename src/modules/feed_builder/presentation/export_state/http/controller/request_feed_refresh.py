from uuid import UUID

from src.modules.feed_builder.application.export_state.command.request_feed_refresh.command import (
    RequestFeedRefreshCommand,
)
from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.presentation.export_state.depends import (
    RequestFeedRefreshHandlerDep,
)
from src.modules.feed_builder.presentation.export_state.http.errors import (
    export_http_error,
)
from src.modules.feed_builder.presentation.export_state.http.request.request_feed_refresh import (
    RequestFeedRefreshRequest,
)
from src.modules.feed_builder.presentation.export_state.http.response.request_feed_refresh import (
    RequestFeedRefreshResponse,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.feed_builder.presentation.feed.export_depends import (
    require_catalog_export_access,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)


async def request_feed_refresh(
    feed_id: UUID,
    payload: RequestFeedRefreshRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: RequestFeedRefreshHandlerDep,
) -> RequestFeedRefreshResponse:
    """Проверяет право публикации и ставит задачу на сохранённой схеме."""
    for action in (
        "feed_builder.feed.read",
        "feed_builder.feed.update",
        "feed_builder.feed.calculation_preview",
        "feed_builder.publication.read",
    ):
        await require_feed_access(
            context, authorization, action=action, feed_id=feed_id
        )
    await require_catalog_export_access(context, authorization)
    principal = context.principal
    assert principal is not None and principal.tenant_id is not None
    try:
        result = await handler.execute(
            RequestFeedRefreshCommand(
                UUID(principal.tenant_id),
                UUID(principal.user_id),
                feed_id,
                payload.expected_version,
            )
        )
    except FeedBuilderDomainError as exc:
        raise export_http_error(exc) from exc
    return RequestFeedRefreshResponse(
        status=result.status, requested_at=result.requested_at
    )
