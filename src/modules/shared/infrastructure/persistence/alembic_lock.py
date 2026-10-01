import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from threading import Lock

_ALEMBIC_LOCK = Lock()


@asynccontextmanager
async def serialized_alembic() -> AsyncIterator[None]:
    """Защищает глобальные proxy Alembic, включая разные event loops."""
    while not _ALEMBIC_LOCK.acquire(blocking=False):
        await asyncio.sleep(0.01)
    try:
        yield
    finally:
        _ALEMBIC_LOCK.release()
