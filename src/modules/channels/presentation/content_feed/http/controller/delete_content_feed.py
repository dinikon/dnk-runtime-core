from uuid import UUID
from fastapi import Query, Response
from src.modules.channels.application.content_feed.command.delete_content_feed.command import (
    DeleteContentFeedCommand,
)
from src.modules.channels.presentation.content_feed.depends import (
    DeleteContentFeedHandlerDep,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def delete_content_feed(
    channel_id: UUID,
    feed_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: DeleteContentFeedHandlerDep,
    expected_revision: int = Query(gt=0),
) -> Response:
    """Авторизует управление и преобразует запрос в конкретный command."""
    _, actor_id = await channel_access(context, authorization, "manage", channel_id)
    await handler.execute(
        DeleteContentFeedCommand(
            channel_id=channel_id, feed_id=feed_id, expected_revision=expected_revision
        )
    )
    return Response(status_code=204)
