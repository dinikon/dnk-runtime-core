from uuid import UUID

from fastapi import HTTPException, Request
from starlette.responses import Response

from src.modules.feed_builder.application.export_state.port.file_content import (
    FeedFileMissingError,
    FeedFileStorageError,
)
from src.modules.feed_builder.application.export_state.query.download_public_feed.query import (
    DownloadPublicFeedQuery,
)
from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.presentation.export_state.depends import (
    DownloadPublicFeedHandlerDep,
    PublicFeedStreamsDep,
)
from src.modules.feed_builder.presentation.export_state.http.response.download_public_feed import (
    close_export_stream,
    download_feed_file,
    feed_file_headers,
    not_modified_feed_file,
)
from src.modules.shared.presentation.http.depends import RequestHostDep


async def download_public_feed(
    public_link_id: UUID,
    request: Request,
    host: RequestHostDep,
    handler: DownloadPublicFeedHandlerDep,
    streams: PublicFeedStreamsDep,
) -> Response:
    """Выдаёт активный CSV по публичному адресу текущего tenant."""
    query = DownloadPublicFeedQuery(host, public_link_id, ExportFormat.CSV)
    file = await handler.execute(query)
    if file is None:
        raise HTTPException(404, "Файл не найден.")
    headers = feed_file_headers(file)
    cached = not_modified_feed_file(request.headers.get("if-none-match"), headers)
    if cached is not None:
        return cached
    try:
        content = await handler.open_file(file)
    except FeedFileMissingError as exc:
        raise HTTPException(404, "Файл не найден.") from exc
    except FeedFileStorageError as exc:
        raise HTTPException(503, "Файл временно недоступен.") from exc
    streams.push_async_callback(close_export_stream, content)
    return download_feed_file(content, query.format, headers)
