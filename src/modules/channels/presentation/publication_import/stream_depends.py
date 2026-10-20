from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import Annotated
from anyio import CancelScope
from fastapi import Depends
from src.modules.channels.application.publication_import.port.files import (
    PublicationImportImageStream,
)


async def close_import_image_stream(stream: PublicationImportImageStream) -> None:
    """Закрывает приватный поток даже при отмене ASGI task group."""
    with CancelScope(shield=True):
        await stream.aclose()


async def get_import_image_streams() -> AsyncIterator[AsyncExitStack]:
    """Владеет потоками и при ошибке завершения function-scoped UoW."""
    async with AsyncExitStack() as streams:
        yield streams


ImportImageStreamsDep = Annotated[AsyncExitStack, Depends(get_import_image_streams)]
