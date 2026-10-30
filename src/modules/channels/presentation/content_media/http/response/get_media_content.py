from src.modules.channels.presentation.content_media.http.response.headers import (
    media_headers,
)
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import Annotated

from anyio import CancelScope
from fastapi import Depends
from starlette.responses import StreamingResponse
from starlette.types import Receive, Scope, Send

from src.modules.channels.application.content_media.query.get_media_content.dto import (
    GetMediaContentResultDTO,
)


class GetMediaContentResponse(StreamingResponse):
    """Передаёт бинарное изображение с закрытием при EOF, disconnect и ошибке commit."""

    def __init__(self, result: GetMediaContentResultDTO) -> None:
        """Принимает поток, открытый после SQL, и не накапливает изображение в памяти."""
        assert result.stream is not None
        self._stream, self._closed = result.stream, False
        super().__init__(self._chunks(), headers=media_headers(result))

    async def _chunks(self) -> AsyncIterator[bytes]:
        """Закрывает источник также при досрочном завершении итерации."""
        try:
            async for chunk in self._stream:
                yield chunk
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        """Защищает освобождение storage stream от отмены ASGI task group."""
        if not self._closed:
            with CancelScope(shield=True):
                await self._stream.aclose()
            self._closed = True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Освобождает поток даже до первой порции или при ошибке отправки."""
        try:
            await super().__call__(scope, receive, send)
        finally:
            await self.aclose()


async def get_media_streams() -> AsyncIterator[AsyncExitStack]:
    """Удерживает cleanup до завершения HTTP-ответа, включая ошибку function-scoped UoW."""
    async with AsyncExitStack() as streams:
        yield streams


MediaStreamsDep = Annotated[AsyncExitStack, Depends(get_media_streams)]
