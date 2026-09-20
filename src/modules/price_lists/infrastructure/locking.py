import asyncio
import hashlib
from contextlib import asynccontextmanager
from typing import AsyncIterator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO


class PostgresPriceListLock:
    """Держит advisory lock на выделенном физическом соединении."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    @asynccontextmanager
    async def hold(
        self, tenant_id: EntityIdVO, price_list_id: PriceListIdVO
    ) -> AsyncIterator[bool]:
        """Serializes syncs for one tenant/price-list on PostgreSQL."""
        digest = hashlib.sha256(f"{tenant_id}:{price_list_id}".encode()).digest()
        lock_key = int.from_bytes(digest[:8], byteorder="big", signed=True)
        bind = self.session_factory.kw["bind"]
        engine = bind.engine if isinstance(bind, AsyncConnection) else bind
        # Pin the physical connection until unlock: committing an AsyncSession
        # alone would return a still-locked connection to the pool.
        async with engine.connect() as connection:
            if connection.dialect.name != "postgresql":
                yield True
                return
            acquired = bool(
                await connection.scalar(
                    text("SELECT pg_try_advisory_lock(:lock_key)"),
                    {"lock_key": lock_key},
                )
            )
            try:
                await connection.commit()
                yield acquired
            finally:
                if acquired:
                    try:
                        await connection.rollback()
                        await asyncio.shield(
                            connection.execute(
                                text("SELECT pg_advisory_unlock(:lock_key)"),
                                {"lock_key": lock_key},
                            )
                        )
                        await connection.commit()
                    except BaseException:
                        await connection.invalidate()
                        raise


__all__ = ["PostgresPriceListLock"]
