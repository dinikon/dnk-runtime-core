from uuid import UUID

from fastapi import HTTPException

from src.modules.feed_builder.application.access_key.command.revoke_feed_access_key.command import (
    RevokeFeedAccessKeyCommand,
)
from src.modules.feed_builder.domain.access_key.error import AccessKeyNotFoundError
from src.modules.feed_builder.domain.access_key.value_object.feed_access_key_id import (
    FeedAccessKeyIdVO,
)
from src.modules.feed_builder.domain.error import FeedBuilderDomainError
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.presentation.access_key.depends import (
    RevokeFeedAccessKeyHandlerDep,
)
from src.modules.feed_builder.presentation.export_state.http.errors import (
    export_http_error,
)


async def revoke_feed_access_key(
    feed_id: UUID, token_id: UUID, handler: RevokeFeedAccessKeyHandlerDep
) -> None:
    """Идемпотентно отзывает один ключ без возврата тела."""
    try:
        await handler.execute(
            RevokeFeedAccessKeyCommand(FeedIdVO(feed_id), FeedAccessKeyIdVO(token_id))
        )
    except AccessKeyNotFoundError as error:
        raise HTTPException(
            404, {"code": "FEED_ACCESS_KEY_NOT_FOUND", "message": str(error)}
        ) from error
    except FeedBuilderDomainError as error:
        raise export_http_error(error) from error
