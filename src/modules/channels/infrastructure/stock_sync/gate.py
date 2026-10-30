import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from hashlib import sha256
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


def channel_stock_lock_key(tenant_id: UUID, channel_id: UUID) -> int:
    """Общий ключ барьера изменения доступа, связей и отправки."""
    return int.from_bytes(
        sha256(f"channels:stock:{tenant_id}:{channel_id}".encode()).digest()[:8],
        signed=True,
    )


@asynccontextmanager
async def stock_channel_gate(
    connection: AsyncConnection, tenant_id: UUID, channel_id: UUID
) -> AsyncIterator[None]:
    """Держит session lock между короткими транзакциями, включая сетевой шаг."""
    key = channel_stock_lock_key(tenant_id, channel_id)
    try:
        await connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": key})
        await connection.commit()
    except BaseException:
        await connection.invalidate()
        raise
    try:
        yield
    finally:
        try:
            if connection.in_transaction():
                await connection.rollback()
            await asyncio.shield(
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": key}
                )
            )
            await connection.commit()
        except BaseException:
            # Session lock не должен оставаться на соединении, возвращённом в pool.
            await connection.invalidate()
            raise
