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
    GetPublicationHandlerDep,
)
from src.modules.channels.application.external_publication.query.get_publication.query import (
    GetPublicationQuery,
)
from src.modules.channels.domain.external_publication.error import (
    PublicationNotFoundError,
)
from src.modules.channels.presentation.external_publication.http.response.get_publication import (
    GetPublicationResponse,
)


async def get_publication(
    channel_id: UUID,
    publication_id: UUID,
    context: AuthenticatedRequestContextDep,
    handler: GetPublicationHandlerDep,
) -> GetPublicationResponse:
    """Возвращает поля карточки, не раскрывая native JSON и настройки подключения."""
    require_channel_context(context)
    try:
        result = await handler.execute(GetPublicationQuery(channel_id, publication_id))
    except (ChannelNotFoundError, PublicationNotFoundError):
        raise HTTPException(404, "Публикация или канал не найдены.") from None
    return GetPublicationResponse.from_dto(result)
