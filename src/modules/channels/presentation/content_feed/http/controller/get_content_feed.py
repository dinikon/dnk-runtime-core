from uuid import UUID
from src.modules.channels.application.content_feed.query.get_content_feed.query import (
    GetContentFeedQuery,
)
from src.modules.channels.presentation.content_feed.depends import (
    GetContentFeedHandlerDep,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.content_feed.http.response.get_content_feed import (
    GetContentFeedResponse,
)


async def get_content_feed(
    channel_id: UUID,
    feed_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: GetContentFeedHandlerDep,
) -> GetContentFeedResponse:
    """Авторизует управление и преобразует запрос в конкретный query."""
    _, actor_id = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        GetContentFeedQuery(channel_id=channel_id, feed_id=feed_id)
    )
    return GetContentFeedResponse.from_dto(result)
