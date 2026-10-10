from uuid import UUID
from datetime import UTC, datetime
from src.modules.files.infrastructure.jobs import schedule_cleanup
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.tenancy.application.ports.files import TenantStorageRegistrationDTO
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.files.application.storage_provider.command.register_system_storage.command import (
    RegisterSystemStorageCommand,
)
from src.modules.files.application.bucket.command.provision_system_bucket.command import (
    ProvisionSystemBucketCommand,
)
from src.modules.files.application.bucket.command.purge_tenant_storage.command import (
    PurgeTenantStorageCommand,
)
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.files.infrastructure.bucket.persistence.repository import (
    SqlAlchemyBucketRepository,
)
from src.modules.files.infrastructure.storage_provider.persistence.repository import (
    SqlAlchemyStorageProviderRepository,
)
from src.modules.files.application.port.storage import StorageResolverProtocol


class FilesTenantStorageAdapter:
    """Адаптирует порт Tenancy к файловым сценариям на общей внешней сессии."""

    def __init__(
        self,
        session: AsyncSession,
        naming: TenantSchemaNaming,
        storage: StorageResolverProtocol | None = None,
    ) -> None:
        """Принимает внешнюю сессию одного tenant и resolver для подмены в тестах."""
        self._session, self._naming, self._storage = session, naming, storage

    async def _bind(self, tenant_id: UUID) -> None:
        """Привязывает одну tenant-схему к соединению перед работой репозиториев."""
        connection = await self._session.connection()
        previous = self._session.info.get("files_tenant_id")
        if previous is not None and previous != tenant_id:
            raise RuntimeError("One storage process must use one tenant.")
        await bind_tenant_schema(connection, tenant_id, self._naming)
        self._session.info["files_tenant_id"] = tenant_id

    async def register(self, tenant_id: UUID) -> TenantStorageRegistrationDTO:
        """Регистрирует намерение без внешнего I/O и commit."""
        await self._bind(tenant_id)
        result = await build_files_handlers(
            self._session, self._storage
        ).register.execute(RegisterSystemStorageCommand(tenant_id))
        await schedule_cleanup(self._session, tenant_id, datetime.now(UTC))
        return TenantStorageRegistrationDTO(result.provider_id, result.bucket_id)

    async def provision(self, tenant_id: UUID) -> None:
        """Продолжает подготовку, используя уже сохранённый бакет."""
        await self._bind(tenant_id)
        providers = SqlAlchemyStorageProviderRepository(self._session)
        provider = await providers.get_system()
        if provider is None:
            raise RuntimeError("Tenant storage must be registered before provisioning.")
        bucket = await SqlAlchemyBucketRepository(self._session).get_system(provider.id)
        if bucket is None:
            raise RuntimeError("Tenant bucket must be registered before provisioning.")
        await build_files_handlers(self._session, self._storage).provision.execute(
            ProvisionSystemBucketCommand(tenant_id, bucket.id.uuid)
        )

    async def is_ready(self, tenant_id: UUID) -> bool:
        """Проверяет только текущую проекцию готовности без изменения данных."""
        await self._bind(tenant_id)
        schema = self._naming.schema_name(TenantIdVO.from_value(tenant_id))
        # Старые схемы должны быть мигрированы и подготовлены отдельной командой.
        if not await self._session.scalar(
            text("SELECT to_regclass(:name)"), {"name": f"{schema}.files_buckets"}
        ):
            return False
        provider = await SqlAlchemyStorageProviderRepository(self._session).get_system()
        if provider is None:
            return False
        bucket = await SqlAlchemyBucketRepository(self._session).get_system(provider.id)
        return bucket is not None and bucket.status == "ready"

    async def purge(self, tenant_id: UUID) -> None:
        """Сохраняет совместимость удаления исторических схем без файлового реестра."""
        await self._bind(tenant_id)
        schema = self._naming.schema_name(TenantIdVO.from_value(tenant_id))
        if not await self._session.scalar(
            text("SELECT to_regclass(:name)"), {"name": f"{schema}.files_buckets"}
        ):
            return
        await build_files_handlers(self._session, self._storage).purge.execute(
            PurgeTenantStorageCommand(tenant_id)
        )
