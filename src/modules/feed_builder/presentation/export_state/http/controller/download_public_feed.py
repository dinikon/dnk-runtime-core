from datetime import UTC
from email.utils import format_datetime
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
)


async def download_public_feed(
    public_link_id: UUID,
    request: Request,
    handler: DownloadPublicFeedHandlerDep,
    streams: PublicFeedStreamsDep,
) -> Response:
    """Выдаёт активный CSV по публичному адресу текущего tenant."""
    return await _download_feed(
        public_link_id, ExportFormat.CSV, request, handler, streams
    )


async def download_public_feed_xml(
    public_link_id: UUID,
    request: Request,
    handler: DownloadPublicFeedHandlerDep,
    streams: PublicFeedStreamsDep,
) -> Response:
    """Открывает активный XML по публичному адресу текущего tenant."""
    return await _download_feed(
        public_link_id, ExportFormat.XML, request, handler, streams
    )


async def _download_feed(
    public_link_id: UUID,
    format: ExportFormat,
    request: Request,
    handler: DownloadPublicFeedHandlerDep,
    streams: PublicFeedStreamsDep,
) -> Response:
    """Разрешает публичный адрес и формат до проверки условного запроса."""
    tenant_id = getattr(request.state, "admitted_tenant_id", None)
    if tenant_id is None:
        raise HTTPException(404, "Файл не найден.")
    file = await handler.execute(DownloadPublicFeedQuery(public_link_id, format))
    if file is None:
        raise HTTPException(404, "Файл не найден.")
    etag = f'"{file.file_id}"'
    published = file.published_at.astimezone(UTC).replace(microsecond=0)
    headers = {
        "ETag": etag,
        "Last-Modified": format_datetime(published, usegmt=True),
        "Cache-Control": "no-cache, must-revalidate",
        "X-Content-Type-Options": "nosniff",
    }
    requested_etag = request.headers.get("if-none-match")
    if requested_etag is not None and any(
        tag.strip().removeprefix("W/") in ("*", etag)
        for tag in requested_etag.split(",")
    ):
        return Response(status_code=304, headers=headers)
    try:
        content = await handler.open_file(tenant_id, file)
    except FeedFileMissingError as exc:
        raise HTTPException(404, "Файл не найден.") from exc
    except FeedFileStorageError as exc:
        raise HTTPException(503, "Файл временно недоступен.") from exc
    streams.push_async_callback(close_export_stream, content)
    return download_feed_file(content, format, headers)
