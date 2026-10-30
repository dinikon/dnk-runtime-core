from uuid import UUID
from src.modules.channels.application.content_feed.command.rotate_feed_access.command import (
    RotateFeedAccessCommand,
)
from src.modules.channels.presentation.content_feed.depends import (
    RotateFeedAccessHandlerDep,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.content_feed.http.request.rotate_feed_access import (
    RotateFeedAccessRequest,
)
from src.modules.channels.presentation.content_feed.http.response.rotate_feed_access import (
    RotateFeedAccessResponse,
)


async def rotate_feed_access(
    channel_id: UUID,
    feed_id: UUID,
    payload: RotateFeedAccessRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: RotateFeedAccessHandlerDep,
) -> RotateFeedAccessResponse:
    """Авторизует управление и преобразует запрос в конкретный command."""
    _, actor_id = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        RotateFeedAccessCommand(
            channel_id=channel_id,
            feed_id=feed_id,
            expected_revision=payload.expected_revision,
            actor_id=actor_id,
        )
    )
    return RotateFeedAccessResponse.from_dto(result)
