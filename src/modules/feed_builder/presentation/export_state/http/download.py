from contextlib import AsyncExitStack
from uuid import UUID

from fastapi import HTTPException, Request
from starlette.responses import Response

from src.modules.feed_builder.application.access_key.token import access_token_digest
from src.modules.feed_builder.application.export_state.port.file_content import (
    FeedFileMissingError,
    FeedFileStorageError,
)
from src.modules.feed_builder.application.export_state.query.download_public_feed.handler import (
    DownloadPublicFeedHandler,
)
from src.modules.feed_builder.application.export_state.query.download_public_feed.query import (
    DownloadPublicFeedQuery,
)
from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.presentation.export_state.http.response.download_public_feed import (
    close_export_stream,
    download_feed_file,
    feed_file_headers,
    not_modified_feed_file,
)


async def serve_active_feed(
    request: Request,
    public_link_id: UUID,
    host: str,
    format: ExportFormat,
    handler: DownloadPublicFeedHandler,
    streams: AsyncExitStack,
) -> Response:
    """Проверяет режим и токен до ответа 304 либо открытия файла."""
    tokens = request.query_params.getlist("token")
    digest = access_token_digest(tokens[0]) if len(tokens) == 1 else None
    file = await handler.execute(
        DownloadPublicFeedQuery(host, public_link_id, format, digest)
    )
    denied = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}
    if file is None:
        raise HTTPException(404, "Файл не найден.", headers=denied)
    headers = feed_file_headers(file, has_token=bool(tokens))
    cached = not_modified_feed_file(request.headers.get("if-none-match"), headers)
    if cached is not None:
        return cached
    try:
        content = await handler.open_file(file)
    except FeedFileMissingError as error:
        raise HTTPException(404, "Файл не найден.", headers=denied) from error
    except FeedFileStorageError as error:
        raise HTTPException(503, "Файл временно недоступен.", headers=denied) from error
    streams.push_async_callback(close_export_stream, content)
    return download_feed_file(content, format, headers)
