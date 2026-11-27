from uuid import UUID

from src.modules.feed_builder.application.access_key.query.list_feed_access_keys.query import (
    ListFeedAccessKeysQuery,
)
from src.modules.feed_builder.domain.feed.error import FeedNotFoundError
from src.modules.feed_builder.presentation.access_key.depends import (
    ListFeedAccessKeysHandlerDep,
)
from src.modules.feed_builder.presentation.access_key.http.response.list_feed_access_keys import (
    ListFeedAccessKeysResponse,
)
from src.modules.feed_builder.presentation.export_state.http.errors import (
    export_http_error,
)


async def list_feed_access_keys(
    feed_id: UUID, handler: ListFeedAccessKeysHandlerDep
) -> ListFeedAccessKeysResponse:
    """Читает разрешённые метаданные токенов выбранного фида."""
    try:
        result = await handler.execute(ListFeedAccessKeysQuery(feed_id))
    except FeedNotFoundError as error:
        raise export_http_error(error) from error
    return ListFeedAccessKeysResponse.model_validate(result)
