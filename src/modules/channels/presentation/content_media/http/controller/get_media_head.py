from uuid import UUID
from fastapi import Query
from src.modules.channels.application.content_media.query.get_media_content.query import (
    GetMediaContentQuery,
)
from src.modules.channels.presentation.content_media.depends import (
    GetMediaContentHandlerDep,
)
from src.modules.channels.presentation.content_media.http.response.get_media_head import (
    GetMediaHeadResponse,
)


async def get_media_head(
    media_id: UUID,
    extension: str,
    handler: GetMediaContentHandlerDep,
    token: str = Query(default="", max_length=256),
) -> GetMediaHeadResponse:
    """Проверяет те же ограничения, что GET, и возвращает только метаданные."""
    return GetMediaHeadResponse.from_dto(
        await handler.execute(
            GetMediaContentQuery(
                media_id, token, metadata_only=True, extension=extension
            )
        )
    )
