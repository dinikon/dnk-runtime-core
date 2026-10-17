from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import Annotated

from anyio import CancelScope
from fastapi import Depends

from src.modules.files.application.port.storage import FileContentStream


async def close_preview_stream(stream: FileContentStream) -> None:
    """Защищает закрытие storage-потока от отмены ASGI task group."""
    with CancelScope(shield=True):
        await stream.aclose()


async def get_preview_streams() -> AsyncIterator[AsyncExitStack]:
    """Закрывает поток после ответа и при ошибке завершения function-scoped UoW."""
    async with AsyncExitStack() as streams:
        yield streams


PreviewStreamsDep = Annotated[AsyncExitStack, Depends(get_preview_streams)]
