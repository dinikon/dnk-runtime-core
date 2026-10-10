from dataclasses import dataclass
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import dnk_config
from src.modules.files.application.storage_provider.command.register_system_storage.handler import (
    RegisterSystemStorageHandler,
)
from src.modules.files.application.bucket.command.provision_system_bucket.handler import (
    ProvisionSystemBucketHandler,
)
from src.modules.files.application.stored_file.command.upload_file.handler import (
    UploadFileHandler,
)
from src.modules.files.application.stored_file.query.get_file_content.handler import (
    GetFileContentHandler,
)
from src.modules.files.application.storage_provider.query.list_providers.handler import (
    ListProvidersHandler,
)
from src.modules.files.application.bucket.query.list_buckets.handler import (
    ListBucketsHandler,
)
from src.modules.files.application.stored_file.command.cleanup_orphaned_objects.handler import (
    CleanupOrphanedObjectsHandler,
)
from src.modules.files.application.bucket.command.purge_tenant_storage.handler import (
    PurgeTenantStorageHandler,
)
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.files.infrastructure.storage.minio_adapter import MinioStorageAdapter
from src.modules.files.infrastructure.storage.resolver import StorageResolver
from src.modules.files.infrastructure.storage_provider.persistence.repository import (
    SqlAlchemyStorageProviderRepository,
)
from src.modules.files.infrastructure.bucket.persistence.repository import (
    SqlAlchemyBucketRepository,
)
from src.modules.files.infrastructure.stored_file.persistence.repository import (
    SqlAlchemyStoredFileRepository,
)
from src.modules.files.infrastructure.persistence.query_repository import (
    SqlAlchemyStorageQueryRepository,
)


@lru_cache(maxsize=1)
def get_storage_resolver() -> StorageResolverProtocol:
    """Создаёт process-local реестр провайдеров из проектного Config."""
    return StorageResolver(
        {("minio", "system_minio"): lambda: MinioStorageAdapter(dnk_config.FILES)}
    )


@dataclass(frozen=True, slots=True)
class FilesHandlers:
    """Внешняя сборка сценариев на одной tenant-сессии, не Application DTO."""

    register: RegisterSystemStorageHandler
    provision: ProvisionSystemBucketHandler
    upload: UploadFileHandler
    content: GetFileContentHandler
    providers: ListProvidersHandler
    buckets: ListBucketsHandler
    cleanup: CleanupOrphanedObjectsHandler
    purge: PurgeTenantStorageHandler


def build_files_handlers(
    session: AsyncSession, storage: StorageResolverProtocol | None = None
) -> FilesHandlers:
    """Подключает все репозитории процесса к сессии внешнего UoW."""
    providers = SqlAlchemyStorageProviderRepository(session)
    buckets = SqlAlchemyBucketRepository(session)
    files = SqlAlchemyStoredFileRepository(session)
    queries = SqlAlchemyStorageQueryRepository(session)
    resolver = storage if storage is not None else get_storage_resolver()
    return FilesHandlers(
        RegisterSystemStorageHandler(providers, buckets),
        ProvisionSystemBucketHandler(providers, buckets, resolver),
        UploadFileHandler(providers, buckets, files, resolver),
        GetFileContentHandler(queries, resolver),
        ListProvidersHandler(queries),
        ListBucketsHandler(queries),
        CleanupOrphanedObjectsHandler(providers, buckets, queries, resolver),
        PurgeTenantStorageHandler(providers, buckets, resolver),
    )
