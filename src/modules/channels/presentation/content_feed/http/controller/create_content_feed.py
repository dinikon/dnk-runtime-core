from uuid import UUID
from src.modules.channels.application.content_feed.command.create_content_feed.command import (
    CreateContentFeedCommand,
)
from src.modules.channels.presentation.content_feed.depends import (
    CreateContentFeedHandlerDep,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.content_feed.http.request.create_content_feed import (
    CreateContentFeedRequest,
)
from src.modules.channels.presentation.content_feed.http.response.create_content_feed import (
    CreateContentFeedResponse,
)
from src.modules.channels.domain.content_feed.value_object import FeedSourceVO


async def create_content_feed(
    channel_id: UUID,
    payload: CreateContentFeedRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: CreateContentFeedHandlerDep,
) -> CreateContentFeedResponse:
    """Авторизует управление и преобразует запрос в конкретный command."""
    _, actor_id = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        CreateContentFeedCommand(
            channel_id=channel_id,
            actor_id=actor_id,
            source=FeedSourceVO(payload.source_schema, payload.source_settings),
            source_url=payload.source_url.get_secret_value(),
        )
    )
    return CreateContentFeedResponse.from_dto(result)
