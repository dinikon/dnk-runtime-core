from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Executable
import hashlib
import sqlalchemy as sa
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.persistence.base import TENANT_SCHEMA_ALIAS


class ScopedRepository:
    """Apply schema translation and transaction-scoped advisory locks."""

    def __init__(self, session: AsyncSession, naming: TenantSchemaNaming):
        self.session, self.naming = session, naming

    def scoped(self, statement: Executable, tenant_id: EntityIdVO) -> Executable:
        return statement.execution_options(
            schema_translate_map={
                TENANT_SCHEMA_ALIAS: self.naming.schema_name(tenant_id)
            }
        )

    async def advisory(self, key: str) -> None:
        digest = int.from_bytes(
            hashlib.sha256(key.encode()).digest()[:8], "big", signed=True
        )
        await self.session.execute(sa.select(sa.func.pg_advisory_xact_lock(digest)))


__all__ = ["ScopedRepository"]
