from collections.abc import AsyncIterator, Mapping

from anyio import CancelScope
from starlette.responses import StreamingResponse

from src.modules.feed_builder.application.export_state.file_format import (
    EXPORT_MEDIA_TYPES,
)
from src.modules.feed_builder.application.export_state.port.file_content import (
    ExportFileContentDTO,
)
from src.modules.feed_builder.domain.feed.enum.export_format import ExportFormat


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
