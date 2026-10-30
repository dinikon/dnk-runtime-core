from uuid import UUID
from src.modules.channels.application.content_feed.query.list_content_feeds.query import (
    ListContentFeedsQuery,
)
from src.modules.channels.presentation.content_feed.depends import (
    ListContentFeedsHandlerDep,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.content_feed.http.response.list_content_feeds import (
    ListContentFeedsResponse,
)


async def list_content_feeds(
    channel_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ListContentFeedsHandlerDep,
) -> ListContentFeedsResponse:
    """Авторизует управление и преобразует запрос в конкретный query."""
    _, actor_id = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(ListContentFeedsQuery(channel_id=channel_id))
    return ListContentFeedsResponse.from_dto(result)
