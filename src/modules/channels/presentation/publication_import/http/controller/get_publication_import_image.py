from collections.abc import AsyncIterator
from uuid import UUID
from fastapi import Query
from src.modules.channels.application.publication_import.query.get_publication_import_image.query import (
    GetPublicationImportImageQuery,
)
from src.modules.channels.presentation.publication_import.depends import (
    GetPublicationImportImageHandlerDep,
)
from src.modules.channels.presentation.depends.access import CatalogCreateContextDep
from src.modules.channels.presentation.publication_import.http.response.get_publication_import_image import (
    PublicationImportImageResponse,
)
from src.modules.channels.presentation.error import http_error
from src.modules.channels.domain.error import ChannelsError
from src.modules.channels.presentation.publication_import.stream_depends import (
    ImportImageStreamsDep,
    close_import_image_stream,
)


async def get_publication_import_image(
    preparation_id: UUID,
    context: CatalogCreateContextDep,
    handler: GetPublicationImportImageHandlerDep,
    streams: ImportImageStreamsDep,
    image_id: str = Query(min_length=1, max_length=200),
) -> PublicationImportImageResponse:
    """Отдаёт приватный stream, закрывая его при отмене или ошибке завершения UoW."""
    try:
        result = await handler.execute(
            GetPublicationImportImageQuery(
                UUID(context.principal.tenant_id),
                UUID(context.principal.user_id),
                preparation_id,
                image_id,
            )
        )
    except ChannelsError as error:
        raise http_error(error) from error
    streams.push_async_callback(close_import_image_stream, result.stream)

    async def chunks() -> AsyncIterator[bytes]:
        """Закрывает ресурс при полном чтении и прерванном ответе."""
        try:
            async for chunk in result.stream:
                yield chunk
        finally:
            await close_import_image_stream(result.stream)

    return PublicationImportImageResponse(
        chunks(),
        media_type=result.content_type,
        headers={
            "Content-Length": str(result.size_bytes),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
