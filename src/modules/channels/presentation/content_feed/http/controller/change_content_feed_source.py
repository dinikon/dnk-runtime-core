from uuid import UUID
from src.modules.channels.application.content_feed.command.change_content_feed_source.command import (
    ChangeContentFeedSourceCommand,
)
from src.modules.channels.presentation.content_feed.depends import (
    ChangeContentFeedSourceHandlerDep,
)
from src.modules.channels.presentation.http.access import channel_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep
from src.modules.channels.presentation.content_feed.http.request.change_content_feed_source import (
    ChangeContentFeedSourceRequest,
)
from src.modules.channels.presentation.content_feed.http.response.change_content_feed_source import (
    ChangeContentFeedSourceResponse,
)
from src.modules.channels.domain.content_feed.value_object import FeedSourceVO


async def change_content_feed_source(
    channel_id: UUID,
    feed_id: UUID,
    payload: ChangeContentFeedSourceRequest,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ChangeContentFeedSourceHandlerDep,
) -> ChangeContentFeedSourceResponse:
    """Авторизует управление и преобразует запрос в конкретный command."""
    _, actor_id = await channel_access(context, authorization, "manage", channel_id)
    result = await handler.execute(
        ChangeContentFeedSourceCommand(
            channel_id=channel_id,
            feed_id=feed_id,
            expected_revision=payload.expected_revision,
            actor_id=actor_id,
            source=FeedSourceVO(payload.source_schema, payload.source_settings),
            source_url=(
                payload.source_url.get_secret_value()
                if payload.source_url is not None
                else None
            ),
        )
    )
    return ChangeContentFeedSourceResponse.from_dto(result)
