from uuid import UUID
from src.modules.channels.application.content_feed.query.preview_content_feed.query import (
    PreviewContentFeedQuery,
)
from src.modules.channels.presentation.content_feed.depends import (
    PreviewContentFeedHandlerDep,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.content_feed.http.response.preview_content_feed import (
    PreviewContentFeedResponse,
)


async def preview_content_feed(
    channel_id: UUID,
    feed_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: PreviewContentFeedHandlerDep,
) -> PreviewContentFeedResponse:
    """Авторизует управление и преобразует запрос в конкретный query."""
    _, actor_id = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        PreviewContentFeedQuery(
            channel_id=channel_id, feed_id=feed_id, actor_id=actor_id
        )
    )
    return PreviewContentFeedResponse.from_dto(result)
