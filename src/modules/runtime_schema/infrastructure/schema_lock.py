from __future__ import annotations

from contextlib import asynccontextmanager
from hashlib import sha1

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_schema.infrastructure.contracts import SchemaLockServiceProtocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlAlchemySchemaLockService(SchemaLockServiceProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    @asynccontextmanager
    async def lock(
        self,
        *,
        tenant_id: EntityIdVO,
        schema: str,
    ):
        bind = self._session.get_bind()
        dialect_name = bind.dialect.name.lower()
        if dialect_name != "postgresql":
            yield
            return

        lock_key = self._lock_key(tenant_id=tenant_id, schema=schema)
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": lock_key},
        )
        yield

    @staticmethod
    def _lock_key(*, tenant_id: EntityIdVO, schema: str) -> int:
        payload = f"{tenant_id.value}:{schema}".encode("utf-8")
        digest = sha1(payload).digest()[:8]
        unsigned = int.from_bytes(digest, byteorder="big", signed=False)
        if unsigned > 2**63 - 1:
            return unsigned - 2**64
        return unsigned


__all__ = ["SqlAlchemySchemaLockService"]
