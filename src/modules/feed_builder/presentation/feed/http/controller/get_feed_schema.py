from uuid import UUID
from fastapi import HTTPException
from src.modules.feed_builder.application.feed.query.get_feed_schema.query import (
    GetFeedSchemaQuery,
)
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.error import FeedNotFoundError
from src.modules.feed_builder.presentation.feed.depends import GetFeedSchemaHandlerDep
from src.modules.feed_builder.presentation.feed.http.response.get_feed_schema import (
    GetFeedSchemaResponse,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def get_feed_schema(
    feed_id: UUID,
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: GetFeedSchemaHandlerDep,
) -> GetFeedSchemaResponse:
    """Читает схему текущего tenant после проверки прав на Feed."""
    await require_feed_access(
        context, authorization, action="feed_builder.feed.read", feed_id=feed_id
    )
    try:
        result = await handler.execute(GetFeedSchemaQuery(FeedIdVO.from_value(feed_id)))
    except FeedNotFoundError as exc:
        raise HTTPException(
            404, {"code": "FEED_NOT_FOUND", "message": str(exc)}
        ) from exc
    return GetFeedSchemaResponse.from_dto(result)
