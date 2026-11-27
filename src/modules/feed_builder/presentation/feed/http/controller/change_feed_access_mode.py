from uuid import UUID

from src.modules.feed_builder.application.feed.command.change_feed_access_mode.command import (
    ChangeFeedAccessModeCommand,
)
from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.domain.feed.enum.feed_access_mode import FeedAccessMode
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.presentation.export_state.http.errors import (
    export_http_error,
)
from src.modules.feed_builder.presentation.feed.access_depends import (
    ChangeFeedAccessModeHandlerDep,
)
from src.modules.feed_builder.presentation.feed.http.request.change_feed_access_mode import (
    ChangeFeedAccessModeRequest,
)
from src.modules.feed_builder.presentation.feed.http.response.change_feed_access_mode import (
    ChangeFeedAccessModeResponse,
)


async def change_feed_access_mode(
    feed_id: UUID,
    payload: ChangeFeedAccessModeRequest,
    handler: ChangeFeedAccessModeHandlerDep,
) -> ChangeFeedAccessModeResponse:
    """Сохраняет режим в транзакции команды настроек."""
    try:
        result = await handler.execute(
            ChangeFeedAccessModeCommand(
                FeedIdVO(feed_id),
                payload.expected_version,
                FeedAccessMode(payload.access_mode),
            )
        )
    except FeedBuilderDomainError as error:
        raise export_http_error(error) from error
    return ChangeFeedAccessModeResponse.model_validate(result)
