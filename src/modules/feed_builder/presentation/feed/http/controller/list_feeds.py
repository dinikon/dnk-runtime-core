from typing import Annotated, Literal
from fastapi import Query, HTTPException
from src.modules.feed_builder.application.feed.query.list_feeds.query import (
    ListFeedsQuery,
)
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.presentation.feed.depends import ListFeedsHandlerDep
from src.modules.feed_builder.presentation.feed.http.response.list_feeds import (
    ListFeedsResponse,
)
from src.modules.feed_builder.presentation.feed.access import require_feed_access
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.identity.presentation.access.depends import AuthorizationServiceDep


async def list_feeds(
    context: AuthenticatedRequestContextDep,
    authorization: AuthorizationServiceDep,
    handler: ListFeedsHandlerDep,
    search: Annotated[str | None, Query(max_length=255)] = None,
    status: Literal["DRAFT", "ACTIVE", "PAUSED", "ARCHIVED"] | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
) -> ListFeedsResponse:
    """Возвращает страницу с поиском; архив виден только при явном фильтре."""
    await require_feed_access(context, authorization, action="feed_builder.feed.read")
    try:
        result = await handler.execute(
            ListFeedsQuery(search=search, status=status, limit=limit, offset=offset)
        )
    except InvalidFeedValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return ListFeedsResponse.from_dto(result)
