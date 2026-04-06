from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.schema_registry.application.ports.tenant_schema_inspector import (
    TenantSchemaInspectorPort,
)
from src.modules.schema_registry.domain.error import UnsupportedSchemaBackendError


class PostgresTenantSchemaInspector(TenantSchemaInspectorPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def schema_exists(self, *, schema_name: str) -> bool:
        self._ensure_postgres()
        result = await self._session.scalar(
            text("""
                SELECT EXISTS(
                    SELECT 1
                    FROM information_schema.schemata
                    WHERE schema_name = :schema_name
                )
                """),
            {"schema_name": schema_name},
        )
        return bool(result)

    async def inspect(self, *, schema_name: str):
        self._ensure_postgres()
        return {"schema_name": schema_name}

    def _ensure_postgres(self) -> None:
        bind = self._session.get_bind()
        if bind.dialect.name != "postgresql":
            raise UnsupportedSchemaBackendError(
                "schema_registry PostgreSQL adapters require a PostgreSQL backend."
            )
