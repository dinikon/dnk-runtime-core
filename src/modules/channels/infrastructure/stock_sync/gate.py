from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncConnection
from src.modules.channels.infrastructure.channel.gate import (
    channel_write_gate,
    channel_write_lock_key,
)


def channel_stock_lock_key(tenant_id: UUID, channel_id: UUID) -> int:
    """Сохраняет совместимость ключа существующих stock-исполнителей."""
    return channel_write_lock_key(tenant_id, channel_id)


@asynccontextmanager
async def stock_channel_gate(
    connection: AsyncConnection, tenant_id: UUID, channel_id: UUID
) -> AsyncIterator[None]:
    """Делегирует существующий барьер общему механизму записи Channels."""
    async with channel_write_gate(connection, tenant_id, channel_id):
        yield
