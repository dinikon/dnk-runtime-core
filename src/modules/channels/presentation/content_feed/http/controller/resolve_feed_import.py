from uuid import UUID
from src.modules.channels.application.content_feed.command.resolve_feed_import.command import (
    ResolveFeedImportCommand,
)
from src.modules.channels.presentation.content_feed.depends import (
    ResolveFeedImportHandlerDep,
)
from src.modules.channels.presentation.content_feed.http.request.resolve_feed_import import (
    ResolveFeedImportRequest,
)
from src.modules.channels.presentation.content_feed.http.response.resolve_feed_import import (
    ResolveFeedImportResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def resolve_feed_import(
    channel_id: UUID,
    feed_id: UUID,
    payload: ResolveFeedImportRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ResolveFeedImportHandlerDep,
) -> ResolveFeedImportResponse:
    """Проверяет права и переводит конкретный HTTP-запрос в команду."""
    _, actor_id = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        ResolveFeedImportCommand(
            channel_id=channel_id,
            feed_id=feed_id,
            actor_id=actor_id,
            expected_revision=payload.expected_revision,
            expected_delivery_revision=payload.expected_delivery_revision,
        )
    )
    return ResolveFeedImportResponse.from_dto(result)
