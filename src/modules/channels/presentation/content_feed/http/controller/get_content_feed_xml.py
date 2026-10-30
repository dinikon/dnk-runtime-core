from uuid import UUID
from fastapi import Query
from src.modules.channels.application.content_feed.query.get_content_feed_xml.query import (
    GetContentFeedXmlQuery,
)
from src.modules.channels.presentation.content_feed.depends import (
    GetContentFeedXmlHandlerDep,
)
from src.modules.channels.presentation.content_feed.http.response.get_content_feed_xml import (
    GetContentFeedXmlResponse,
)


async def get_content_feed_xml(
    feed_id: UUID,
    handler: GetContentFeedXmlHandlerDep,
    token: str = Query(default="", max_length=256),
) -> GetContentFeedXmlResponse:
    """Передаёт единственный ограниченный токен, без cookies и actor из запроса."""
    return GetContentFeedXmlResponse(
        await handler.execute(GetContentFeedXmlQuery(feed_id, token))
    )
