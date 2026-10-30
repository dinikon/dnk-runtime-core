from uuid import UUID
from src.modules.channels.application.content_feed.command.attach_feed_import.command import (
    AttachFeedImportCommand,
)
from src.modules.channels.presentation.content_feed.depends import (
    AttachFeedImportHandlerDep,
)
from src.modules.channels.presentation.content_feed.http.request.attach_feed_import import (
    AttachFeedImportRequest,
)
from src.modules.channels.presentation.content_feed.http.response.attach_feed_import import (
    AttachFeedImportResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def attach_feed_import(
    channel_id: UUID,
    feed_id: UUID,
    payload: AttachFeedImportRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: AttachFeedImportHandlerDep,
) -> AttachFeedImportResponse:
    """Проверяет права и переводит конкретный HTTP-запрос в команду."""
    _, actor_id = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        AttachFeedImportCommand(
            channel_id=channel_id,
            feed_id=feed_id,
            actor_id=actor_id,
            expected_revision=payload.expected_revision,
            expected_delivery_revision=payload.expected_delivery_revision,
            external_id=payload.external_id,
        )
    )
    return AttachFeedImportResponse.from_dto(result)
