from collections.abc import AsyncIterator
from urllib.parse import quote

from starlette.responses import StreamingResponse
from starlette.types import Receive, Scope, Send

from src.modules.files.application.port.storage import FileContentStream
from src.modules.files.application.stored_file.query.get_file_preview.dto import (
    GetFilePreviewResultDTO,
)
from src.modules.files.presentation.stored_file.stream_depends import (
    close_preview_stream,
)


class GetFilePreviewResponse(StreamingResponse):
    """Выдаёт бинарный предпросмотр с безопасными заголовками и управлением ресурсом."""

    def __init__(
        self,
        *,
        stream: FileContentStream,
        name: str,
        content_type: str,
        size_bytes: int,
    ) -> None:
        """Настраивает inline-ответ без кеширования и выполнения активного содержимого."""
        self._stream = stream
        self._closed = False
        super().__init__(
            self._chunks(),
            headers={
                "Content-Type": content_type,
                "Content-Length": str(size_bytes),
                "Content-Disposition": f"inline; filename*=UTF-8''{quote(name, safe='')}",
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": (
                    "sandbox allow-same-origin; default-src 'none'; "
                    "img-src 'self' data:; media-src 'self' blob:; frame-ancestors 'self'"
                ),
                "X-Frame-Options": "SAMEORIGIN",
                "Referrer-Policy": "no-referrer",
            },
        )

    @classmethod
    def from_dto(cls, result: GetFilePreviewResultDTO) -> "GetFilePreviewResponse":
        """Явно преобразует результат сценария в собственный HTTP-ответ."""
        return cls(
            stream=result.stream,
            name=result.name,
            content_type=result.content_type,
            size_bytes=result.size_bytes,
        )

    async def _chunks(self) -> AsyncIterator[bytes]:
        """Передаёт порции без накопления файла и закрывает поток при прерывании."""
        try:
            async for chunk in self._stream:
                yield chunk
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        """Идемпотентно освобождает storage-поток после завершения отправки."""
        if not self._closed:
            await close_preview_stream(self._stream)
            self._closed = True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Закрывает ресурс также при disconnect до первой порции или ошибке send."""
        try:
            await super().__call__(scope, receive, send)
        finally:
            await self.aclose()
