from uuid import UUID
from fastapi import HTTPException
from src.modules.feed_builder.application.feed.query.get_feed.query import GetFeedQuery
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.error import FeedNotFoundError
from src.modules.feed_builder.presentation.feed.depends import GetFeedHandlerDep
from src.modules.feed_builder.presentation.feed.http.response.get_feed import (
    GetFeedResponse,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def get_feed(
    feed_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: GetFeedHandlerDep,
) -> GetFeedResponse:
    """Возвращает карточку текущего tenant, включая архивную запись."""
    await require_feed_access(
        context, authorization, action="feed_builder.feed.read", feed_id=feed_id
    )
    try:
        result = await handler.execute(
            GetFeedQuery(feed_id=FeedIdVO.from_value(feed_id))
        )
    except FeedNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return GetFeedResponse.from_dto(result)
