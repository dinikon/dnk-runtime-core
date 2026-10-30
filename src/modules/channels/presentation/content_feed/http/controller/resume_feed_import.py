from uuid import UUID
from src.modules.channels.application.content_feed.command.resume_feed_import.command import (
    ResumeFeedImportCommand,
)
from src.modules.channels.presentation.content_feed.depends import (
    ResumeFeedImportHandlerDep,
)
from src.modules.channels.presentation.content_feed.http.request.resume_feed_import import (
    ResumeFeedImportRequest,
)
from src.modules.channels.presentation.content_feed.http.response.resume_feed_import import (
    ResumeFeedImportResponse,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def resume_feed_import(
    channel_id: UUID,
    feed_id: UUID,
    payload: ResumeFeedImportRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ResumeFeedImportHandlerDep,
) -> ResumeFeedImportResponse:
    """Проверяет права и переводит конкретный HTTP-запрос в команду."""
    _, actor_id = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        ResumeFeedImportCommand(
            channel_id=channel_id,
            feed_id=feed_id,
            actor_id=actor_id,
            expected_revision=payload.expected_revision,
            expected_delivery_revision=payload.expected_delivery_revision,
        )
    )
    return ResumeFeedImportResponse.from_dto(result)
