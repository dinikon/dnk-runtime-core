from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.schema import CreateSchema

from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    TenantMigrator,
    lock_tenant_schema,
    schema_exists,
)
from src.modules.tenancy.application.ports.schema_bootstrap import (
    TenantSchemaBootstrapContext,
)
from src.modules.tenancy.domain.tenant.schema_error import (
    TenantSchemaAlreadyExistsError,
)


class AlembicTenantSchemaBootstrapAdapter:
    """Создаёт tenant-схему и применяет миграции в текущей UoW-сессии."""

    def __init__(self, session: AsyncSession, migrator: TenantMigrator) -> None:
        self._session = session
        self._migrator = migrator

    async def bootstrap(self, *, context: TenantSchemaBootstrapContext) -> None:
        """Выполняет транзакционный bootstrap без внутреннего commit."""
        connection = await self._session.connection()
        await lock_tenant_schema(connection, context.schema_name)
        if await schema_exists(connection, context.schema_name):
            raise TenantSchemaAlreadyExistsError(context.schema_name)
        await connection.execute(CreateSchema(context.schema_name))
        await self._migrator.upgrade(connection, context.schema_name)
