from uuid import UUID
from src.modules.channels.application.content_feed.command.enable_content_feed.command import (
    EnableContentFeedCommand,
)
from src.modules.channels.presentation.content_feed.depends import (
    EnableContentFeedHandlerDep,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.content_feed.http.request.enable_content_feed import (
    EnableContentFeedRequest,
)
from src.modules.channels.presentation.content_feed.http.response.enable_content_feed import (
    EnableContentFeedResponse,
)


async def enable_content_feed(
    channel_id: UUID,
    feed_id: UUID,
    payload: EnableContentFeedRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: EnableContentFeedHandlerDep,
) -> EnableContentFeedResponse:
    """Авторизует управление и преобразует запрос в конкретный command."""
    _, actor_id = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        EnableContentFeedCommand(
            channel_id=channel_id,
            feed_id=feed_id,
            expected_revision=payload.expected_revision,
            actor_id=actor_id,
        )
    )
    return EnableContentFeedResponse.from_dto(result)
