from uuid import UUID
from src.modules.channels.application.content_feed.command.disable_content_feed.command import (
    DisableContentFeedCommand,
)
from src.modules.channels.presentation.content_feed.depends import (
    DisableContentFeedHandlerDep,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.content_feed.http.request.disable_content_feed import (
    DisableContentFeedRequest,
)
from src.modules.channels.presentation.content_feed.http.response.disable_content_feed import (
    DisableContentFeedResponse,
)


async def disable_content_feed(
    channel_id: UUID,
    feed_id: UUID,
    payload: DisableContentFeedRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: DisableContentFeedHandlerDep,
) -> DisableContentFeedResponse:
    """Авторизует управление и преобразует запрос в конкретный command."""
    _, actor_id = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        DisableContentFeedCommand(
            channel_id=channel_id,
            feed_id=feed_id,
            expected_revision=payload.expected_revision,
            actor_id=actor_id,
        )
    )
    return DisableContentFeedResponse.from_dto(result)
