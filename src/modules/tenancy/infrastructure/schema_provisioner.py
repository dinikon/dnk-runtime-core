from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.tenancy.application.admin_onboarding.ports.storage import (
    TenantSchemaProvisionerProtocol,
)


class SqlAlchemyTenantSchemaProvisioner(TenantSchemaProvisionerProtocol):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_schema(self, schema: str) -> None:
        bind = self._session.get_bind()
        if bind.dialect.name != "postgresql":
            return

        quoted_schema = bind.dialect.identifier_preparer.quote(schema)
        await self._session.execute(
            text(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema}")
        )
