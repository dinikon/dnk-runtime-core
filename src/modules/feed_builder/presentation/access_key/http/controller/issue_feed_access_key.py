from uuid import UUID

from fastapi import Response

from src.modules.feed_builder.application.access_key.command.issue_feed_access_key.command import (
    IssueFeedAccessKeyCommand,
)
from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.presentation.access_key.depends import (
    IssueFeedAccessKeyHandlerDep,
)
from src.modules.feed_builder.presentation.access_key.http.request.issue_feed_access_key import (
    IssueFeedAccessKeyRequest,
)
from src.modules.feed_builder.presentation.access_key.http.response.issue_feed_access_key import (
    IssueFeedAccessKeyResponse,
)
from src.modules.feed_builder.presentation.export_state.http.errors import (
    export_http_error,
)


async def issue_feed_access_key(
    feed_id: UUID,
    payload: IssueFeedAccessKeyRequest,
    response: Response,
    handler: IssueFeedAccessKeyHandlerDep,
) -> IssueFeedAccessKeyResponse:
    """Выпускает токен и отключает кеширование ответа с секретом."""
    try:
        result = await handler.execute(
            IssueFeedAccessKeyCommand(
                FeedIdVO(feed_id), payload.name, payload.expires_at
            )
        )
    except FeedBuilderDomainError as error:
        raise export_http_error(error) from error
    response.headers["Cache-Control"] = "no-store"
    return IssueFeedAccessKeyResponse.model_validate(result)
