from uuid import UUID
from src.modules.channels.application.content_feed.query.get_feed_import.query import (
    GetFeedImportQuery,
)
from src.modules.channels.presentation.content_feed.depends import (
    GetFeedImportHandlerDep,
)
from src.modules.channels.presentation.content_feed.http.response.get_feed_import import (
    GetFeedImportResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def get_feed_import(
    channel_id: UUID,
    feed_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: GetFeedImportHandlerDep,
) -> GetFeedImportResponse:
    """Читает статус только после проверки tenant и права управления каналом."""
    await channel_access(context, authorization, "manage", channel_id)
    return GetFeedImportResponse.from_dto(
        await handler.execute(GetFeedImportQuery(channel_id, feed_id))
    )
