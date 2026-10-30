from uuid import UUID
from src.modules.channels.application.content_feed.command.request_feed_import.command import (
    RequestFeedImportCommand,
)
from src.modules.channels.presentation.content_feed.depends import (
    RequestFeedImportHandlerDep,
)
from src.modules.channels.presentation.content_feed.http.request.request_feed_import import (
    RequestFeedImportRequest,
)
from src.modules.channels.presentation.content_feed.http.response.request_feed_import import (
    RequestFeedImportResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def request_feed_import(
    channel_id: UUID,
    feed_id: UUID,
    payload: RequestFeedImportRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: RequestFeedImportHandlerDep,
) -> RequestFeedImportResponse:
    """Проверяет права и переводит конкретный HTTP-запрос в команду."""
    _, actor_id = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        RequestFeedImportCommand(
            channel_id=channel_id,
            feed_id=feed_id,
            actor_id=actor_id,
            expected_revision=payload.expected_revision,
            expected_delivery_revision=payload.expected_delivery_revision,
            request_id=payload.request_id,
            force_update=payload.force_update,
        )
    )
    return RequestFeedImportResponse.from_dto(result)
