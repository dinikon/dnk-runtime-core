import logging
from sqlalchemy import select
from src.modules.control_plane.infrastructure.models import InstallationModel
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_gate import TenantGate
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.tenancy.infrastructure.adapter.files import FilesTenantStorageAdapter
from src.modules.tenancy.infrastructure.repository.tenant_repository import (
    SqlAlchemyTenantRepository,
)
from src.modules.tenancy.application.tenant.command.activate_tenant.command import (
    ActivateTenantCommand,
)
from src.modules.tenancy.application.tenant.command.activate_tenant.handler import (
    ActivateTenantHandler,
)
from src.modules.files.application.port.storage import StorageResolverProtocol

logger = logging.getLogger(__name__)


async def prepare_tenant_storage(
    sessions: async_sessionmaker[AsyncSession],
    naming: TenantSchemaNaming,
    tenant_id: UUID,
    *,
    activate: bool = False,
    storage: StorageResolverProtocol | None = None,
) -> None:
    """Идемпотентно регистрирует и подготавливает хранилище, сохраняя admission."""
    async with TenantGate(sessions).hold(tenant_id) as connection:
        factory = async_sessionmaker(connection, expire_on_commit=False)
        async with factory() as session:
            tenant = await SqlAlchemyTenantRepository(session).get_by_id(
                TenantIdVO.from_value(tenant_id)
            )
            if tenant is None:
                raise RuntimeError("Tenant does not exist.")
            if tenant.status.value not in {"active", "provisioning", "freeze"}:
                raise RuntimeError("Tenant is unavailable for storage preparation.")
            schema = naming.schema_name(TenantIdVO.from_value(tenant_id))
            migrator = TenantMigrator()
            if await migrator.current(connection, schema) != (migrator.head(),):
                raise RuntimeError(
                    "Upgrade tenant migrations before preparing storage."
                )
            if activate and await session.scalar(
                select(InstallationModel.core_tenant_id)
                .where(InstallationModel.runtime_tenant_id == tenant_id)
                .with_for_update()
            ):
                raise RuntimeError(
                    "Control plane must resume managed tenant installation."
                )
            adapter = FilesTenantStorageAdapter(session, naming, storage)
            await adapter.register(tenant_id)
            await session.commit()
            await adapter.provision(tenant_id)
            await session.commit()
            logger.info(
                "Tenant storage prepared",
                extra={"event": "files.storage.prepared", "tenant_id": str(tenant_id)},
            )
            if activate:
                await ActivateTenantHandler(
                    SqlAlchemyTenantRepository(session), adapter
                ).execute(ActivateTenantCommand(tenant_id))
                await session.commit()
                logger.info(
                    "Tenant activated",
                    extra={
                        "event": "tenancy.activate.committed",
                        "tenant_id": str(tenant_id),
                    },
                )
