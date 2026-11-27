from collections.abc import AsyncIterator, Mapping
from datetime import UTC
from email.utils import format_datetime

from anyio import CancelScope
from starlette.responses import Response, StreamingResponse

from src.modules.feed_builder.application.export_state.file_format import (
    EXPORT_MEDIA_TYPES,
)
from src.modules.feed_builder.application.export_state.port.file_content import (
    ExportFileContentDTO,
)
from src.modules.feed_builder.application.export_state.query.download_public_feed.dto import (
    DownloadPublicFeedResultDTO,
)
from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat
from src.modules.feed_builder.domain.feed.enum.feed_access_mode import FeedAccessMode


def feed_file_headers(
    file: DownloadPublicFeedResultDTO, *, has_token: bool
) -> dict[str, str]:
    """Формирует заголовки после проверки доступа к активному файлу."""
    published = file.published_at.astimezone(UTC).replace(microsecond=0)
    sensitive = has_token or file.access_mode is FeedAccessMode.PRIVATE
    return {
        "ETag": f'"{file.file_id}"',
        "Last-Modified": format_datetime(published, usegmt=True),
        "Cache-Control": (
            "private, no-store" if sensitive else "no-cache, must-revalidate"
        ),
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
    }


def not_modified_feed_file(
    requested_etag: str | None, headers: Mapping[str, str]
) -> Response | None:
    """Возвращает 304, когда переданный ETag подходит активному файлу."""
    if requested_etag is not None and any(
        tag.strip().removeprefix("W/") in ("*", headers["ETag"])
        for tag in requested_etag.split(",")
    ):
        return Response(status_code=304, headers=headers)
    return None


async def close_export_stream(file: ExportFileContentDTO) -> None:
    """Закрывает поток даже при отмене запроса."""
    with CancelScope(shield=True):
        await file.stream.aclose()


def download_feed_file(
    file: ExportFileContentDTO, format: ExportFormat, headers: Mapping[str, str]
) -> StreamingResponse:
    """Выбирает открытие XML в браузере или скачивание CSV-вложения."""

    async def chunks() -> AsyncIterator[bytes]:
        """Передаёт порции открытого потока."""
        async for chunk in file.stream:
            yield chunk

    disposition = "inline" if format is ExportFormat.XML else "attachment"
    return StreamingResponse(
        chunks(),
        media_type=EXPORT_MEDIA_TYPES[format],
        headers={
            **headers,
            "Content-Disposition": f'{disposition}; filename="feed.{format.value}"',
            "Content-Length": str(file.size_bytes),
        },
    )
