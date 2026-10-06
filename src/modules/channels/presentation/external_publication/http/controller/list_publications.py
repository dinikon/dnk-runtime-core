from uuid import UUID
from fastapi import HTTPException, Query
from src.modules.identity.presentation.auth.depends import (
    AuthenticatedRequestContextDep,
)
from src.modules.channels.presentation.channel.http.context import (
    require_channel_context,
)
from src.modules.channels.domain.channel.error import ChannelNotFoundError

from src.modules.channels.presentation.external_publication.depends import (
    ListPublicationsHandlerDep,
)
from src.modules.channels.application.external_publication.query.list_publications.query import (
    ListPublicationsQuery,
)
from src.modules.channels.presentation.external_publication.http.response.list_publications import (
    ListPublicationsResponse,
)


async def list_publications(
    channel_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: ListPublicationsHandlerDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
) -> ListPublicationsResponse:
    """Возвращает страницу локальных карточек после проверки tenant контекста."""
    require_channel_context(context)
    try:
        result = await handler.execute(ListPublicationsQuery(channel_id, offset, limit))
    except ChannelNotFoundError:
        raise HTTPException(404, "Канал не найден.") from None
    return ListPublicationsResponse.from_dto(result)
