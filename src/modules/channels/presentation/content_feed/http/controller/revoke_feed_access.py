from uuid import UUID
from src.modules.channels.application.content_feed.command.revoke_feed_access.command import (
    RevokeFeedAccessCommand,
)
from src.modules.channels.presentation.content_feed.depends import (
    RevokeFeedAccessHandlerDep,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.content_feed.http.request.revoke_feed_access import (
    RevokeFeedAccessRequest,
)
from src.modules.channels.presentation.content_feed.http.response.revoke_feed_access import (
    RevokeFeedAccessResponse,
)


async def revoke_feed_access(
    channel_id: UUID,
    feed_id: UUID,
    payload: RevokeFeedAccessRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: RevokeFeedAccessHandlerDep,
) -> RevokeFeedAccessResponse:
    """Авторизует управление и преобразует запрос в конкретный command."""
    _, actor_id = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        RevokeFeedAccessCommand(
            channel_id=channel_id,
            feed_id=feed_id,
            expected_revision=payload.expected_revision,
            actor_id=actor_id,
        )
    )
    return RevokeFeedAccessResponse.from_dto(result)
