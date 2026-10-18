from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession, AsyncConnection, async_sessionmaker
from src.config import dnk_config
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_gate import TenantGate
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)


@asynccontextmanager
async def tenant_scope(
    sessions: async_sessionmaker[AsyncSession], tenant_id: UUID
) -> AsyncIterator[AsyncConnection]:
    """Удерживает admission между короткими UoW, без транзакции во время HTTP."""
    async with TenantGate(sessions).hold(tenant_id) as connection:
        await bind_tenant_schema(
            connection, tenant_id, TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
        )
        yield connection
