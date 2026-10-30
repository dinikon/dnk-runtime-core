from uuid import UUID
from fastapi import Query
from anyio import CancelScope

from src.modules.channels.application.content_media.query.get_media_content.query import (
    GetMediaContentQuery,
)
from src.modules.channels.presentation.content_media.depends import (
    GetMediaContentHandlerDep,
)
from src.modules.channels.presentation.content_media.http.response.get_media_content import (
    GetMediaContentResponse,
    MediaStreamsDep,
)


async def get_media_content(
    media_id: UUID,
    extension: str,
    handler: GetMediaContentHandlerDep,
    streams: MediaStreamsDep,
    token: str = Query(default="", max_length=256),
) -> GetMediaContentResponse:
    """Читает конкретное изображение по токену без сессии, cookies и CSRF."""
    result = await handler.execute(
        GetMediaContentQuery(media_id, token, extension=extension)
    )
    try:
        response = GetMediaContentResponse(result)
    except BaseException:
        assert result.stream is not None
        with CancelScope(shield=True):
            await result.stream.aclose()
        raise
    streams.push_async_callback(response.aclose)
    return response
