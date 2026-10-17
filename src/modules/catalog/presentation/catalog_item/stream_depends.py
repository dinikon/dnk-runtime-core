from anyio import CancelScope
from src.modules.catalog.application.catalog_item.port.files import CatalogImageStream
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import Annotated
from fastapi import Depends


async def close_image_stream(stream: CatalogImageStream) -> None:
    """Защищает освобождение внешнего ресурса от отмены ASGI stream task."""
    with CancelScope(shield=True):
        await stream.aclose()


async def get_image_streams() -> AsyncIterator[AsyncExitStack]:
    """Закрывает файловые потоки после ответа, отмены или ошибки commit UoW."""
    async with AsyncExitStack() as streams:
        yield streams


ImageStreamsDep = Annotated[AsyncExitStack, Depends(get_image_streams)]
