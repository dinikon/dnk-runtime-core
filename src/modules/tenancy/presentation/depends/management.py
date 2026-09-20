from dataclasses import dataclass

from src.modules.shared.infrastructure.persistence.tenant_gate import (
    TenantGate,
    TenantUnavailable,
)
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool
from sqlalchemy import select
from src.modules.shared.infrastructure.persistence.tenant_gate import DELETING
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel

from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.infrastructure.persistence.tenant_migrations import (
    TenantMigrationError,
    TenantMigrator,
)
from src.modules.shared.infrastructure.persistence.unit_of_work import UnitOfWork
from src.modules.tenancy.domain.tenant.value_object import TenantIdVO
from src.modules.tenancy.infrastructure.repository import SqlAlchemyTenantRepository


@dataclass(frozen=True, slots=True)
class TenantMigrationStatus:
    """Статус версии одной tenant-схемы для management CLI."""

    tenant_id: UUID
    schema_name: str
    revisions: tuple[str, ...]
    head: str | None


class TenantMigrationManagement:
    """Собирает session-bound зависимости tenant migration команд."""

    def __init__(
        self,
        session_factory: async_sessionmaker,
        database_url: str | URL,
        naming: TenantSchemaNaming,
        migrator: TenantMigrator,
    ) -> None:
        self._session_factory = session_factory
        self._database_url = database_url
        self._naming = naming
        self._migrator = migrator

    async def list_ids(self) -> list[UUID]:
        """Читает tenants без создания отсутствующих схем."""
        async with UnitOfWork(self._session_factory) as uow:
            ids = await uow.session.scalars(
                select(TenantModel.id).where(TenantModel.status.not_in(DELETING))
            )
            return sorted(ids, key=str)

    async def run_one(self, tenant_id: UUID, *, upgrade: bool) -> TenantMigrationStatus:
        try:
            async with TenantGate(self._session_factory).hold(tenant_id):
                return await self._run_one(tenant_id, upgrade=upgrade)
        except TenantUnavailable:
            raise TenantMigrationError("Tenant is unavailable for migration.") from None

    async def _run_one(
        self, tenant_id: UUID, *, upgrade: bool
    ) -> TenantMigrationStatus:
        """Обрабатывает ровно один tenant в собственной транзакции."""
        typed_id = TenantIdVO.from_value(tenant_id)
        async with UnitOfWork(self._session_factory) as uow:
            tenant = await SqlAlchemyTenantRepository(uow.session).get_by_id(typed_id)
            if tenant is None:
                raise TenantMigrationError(f"Tenant '{tenant_id}' does not exist.")
            schema_name = self._naming.schema_name(typed_id)
            connection = await uow.session.connection()
            if upgrade:
                await self._migrator.upgrade(connection, schema_name)
            return TenantMigrationStatus(
                tenant_id,
                schema_name,
                await self._migrator.current(connection, schema_name),
                self._migrator.head(),
            )

    async def revision(self, tenant_id: UUID, message: str):
        try:
            async with TenantGate(self._session_factory).hold(tenant_id):
                return await self._revision(tenant_id, message)
        except TenantUnavailable:
            raise TenantMigrationError("Tenant is unavailable for migration.") from None

    async def _revision(self, tenant_id: UUID, message: str):
        """Генерирует черновик через отдельный engine для reflection."""
        status = await self._run_one(tenant_id, upgrade=False)
        engine = create_async_engine(self._database_url, poolclass=NullPool)
        try:
            async with engine.begin() as connection:
                return await self._migrator.revision(
                    connection, status.schema_name, message
                )
        finally:
            await engine.dispose()


def build_tenant_migration_management() -> TenantMigrationManagement:
    """Создаёт management composition без tenant-bound repository."""
    from src.config import dnk_config
    from src.modules.shared.infrastructure.persistence.database_helper import db_helper

    return TenantMigrationManagement(
        db_helper.session_factory,
        db_helper.engine.url,
        TenantSchemaNaming(dnk_config.SCHEMA_PREFIX),
        TenantMigrator(),
    )
