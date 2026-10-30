from src.modules.files.application.artifact.service import ArtifactFilesService
from src.modules.files.application.stored_file.port.usage import FileUsagePort
from src.modules.files.infrastructure.file_usage import ConsumerFileUsage
from src.modules.catalog.application.catalog_item.query.find_used_image_files.handler import (
    FindUsedImageFilesHandler as CatalogImages,
)
from src.modules.catalog.infrastructure.catalog_item.image_usage import (
    SqlAlchemyCatalogImageUsage,
)
from src.modules.channels.application.content_media.query.find_used_image_files.handler import (
    FindUsedImageFilesHandler as ChannelImages,
)
from src.modules.channels.infrastructure.content_media.query_repository import (
    SqlAlchemyContentMediaQueryRepository,
)
from src.modules.files.application.stored_file.command.lock_ready_file.handler import (
    LockReadyFileHandler,
)
from src.modules.files.application.stored_file.command.purge_file.handler import (
    PurgeFileHandler,
)
from src.modules.files.application.stored_file.command.cleanup_expired_trash.handler import (
    CleanupExpiredTrashHandler,
)
from dataclasses import dataclass
from src.modules.files.application.stored_file.command.request_trash_empty.handler import (
    RequestTrashEmptyHandler,
)
from src.modules.files.application.stored_file.command.empty_trash.handler import (
    EmptyTrashHandler,
)
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
from src.modules.files.application.stored_file.query.get_file_preview.handler import (
    GetFilePreviewHandler,
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
from src.modules.files.infrastructure.stored_file.persistence.query_repository import (
    SqlAlchemyStoredFileQueryRepository,
)
from src.modules.files.application.stored_file.query.list_files.handler import (
    ListFilesHandler,
)
from src.modules.files.application.stored_file.query.list_trashed_files.handler import (
    ListTrashedFilesHandler,
)
from src.modules.files.application.stored_file.query.get_files_overview.handler import (
    GetFilesOverviewHandler,
)

from src.modules.files.application.stored_file.command.trash_file.handler import (
    TrashFileHandler,
)
from src.modules.files.application.stored_file.command.restore_file.handler import (
    RestoreFileHandler,
)
from src.modules.files.application.stored_file.command.request_file_purge.handler import (
    RequestFilePurgeHandler,
)
from src.modules.files.infrastructure.stored_file.jobs.purge_queue import (
    ScheduledFilePurgeQueue,
)
from src.modules.shared.application.jobs.schedule_scheduled_job_use_case import (
    ScheduleScheduledJobUseCase,
)
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator


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
    files: ListFilesHandler
    trash: ListTrashedFilesHandler
    overview: GetFilesOverviewHandler
    trash_file: TrashFileHandler
    restore: RestoreFileHandler
    request_purge: RequestFilePurgeHandler
    purge_file: PurgeFileHandler
    cleanup_trash: CleanupExpiredTrashHandler
    preview: GetFilePreviewHandler
    request_trash_empty: RequestTrashEmptyHandler
    empty_trash: EmptyTrashHandler
    lock_ready: LockReadyFileHandler


def build_files_handlers(
    session: AsyncSession,
    storage: StorageResolverProtocol | None = None,
    *,
    clock: ClockPort | None = None,
    uuid_generator: UUIdGeneratorProtocol | None = None,
    usage: FileUsagePort | None = None,
) -> FilesHandlers:
    """Подключает все репозитории процесса к сессии внешнего UoW."""
    providers = SqlAlchemyStorageProviderRepository(session)
    buckets = SqlAlchemyBucketRepository(session)
    files = SqlAlchemyStoredFileRepository(session)
    queries = SqlAlchemyStorageQueryRepository(session)
    file_queries = SqlAlchemyStoredFileQueryRepository(session)
    resolver = storage if storage is not None else get_storage_resolver()
    actual_clock = clock if clock is not None else UtcClock()
    actual_uuid = uuid_generator if uuid_generator is not None else UUID7Generator()
    file_usage = usage if usage is not None else build_file_usage(session)
    jobs = build_scheduled_job_repository(session)
    queue = ScheduledFilePurgeQueue(
        ScheduleScheduledJobUseCase(
            repository=jobs,
            clock=actual_clock,
            uuid_generator=actual_uuid,
        ),
        jobs,
    )
    return FilesHandlers(
        RegisterSystemStorageHandler(providers, buckets),
        ProvisionSystemBucketHandler(providers, buckets, resolver),
        UploadFileHandler(providers, buckets, files, resolver),
        GetFileContentHandler(queries, resolver),
        ListProvidersHandler(queries),
        ListBucketsHandler(queries),
        CleanupOrphanedObjectsHandler(providers, buckets, queries, resolver),
        PurgeTenantStorageHandler(providers, buckets, resolver),
        ListFilesHandler(file_queries),
        ListTrashedFilesHandler(file_queries),
        GetFilesOverviewHandler(file_queries),
        TrashFileHandler(files, actual_clock, file_usage),
        RestoreFileHandler(files, buckets, providers, resolver, actual_clock),
        RequestFilePurgeHandler(files, queue, actual_clock, actual_uuid, file_usage),
        PurgeFileHandler(files, buckets, providers, resolver, file_usage),
        CleanupExpiredTrashHandler(files, file_queries, queue, actual_uuid, file_usage),
        GetFilePreviewHandler(queries, resolver),
        RequestTrashEmptyHandler(queue, actual_clock, actual_uuid),
        EmptyTrashHandler(
            files, file_queries, queue, actual_clock, actual_uuid, file_usage
        ),
        LockReadyFileHandler(files),
    )


def build_artifact_files_facade(session: AsyncSession) -> ArtifactFilesService:
    """Собирает публичный контракт двухфазной загрузки на общей сессии."""
    return ArtifactFilesService(
        SqlAlchemyStoredFileRepository(session),
        SqlAlchemyBucketRepository(session),
        SqlAlchemyStorageProviderRepository(session),
        SqlAlchemyStorageQueryRepository(session),
    )


def build_file_usage(session: AsyncSession) -> FileUsagePort:
    """Подключает владельцев ссылок на внешней границе Files без опционального bypass."""
    return ConsumerFileUsage(
        catalog=CatalogImages(SqlAlchemyCatalogImageUsage(session)),
        channels=ChannelImages(SqlAlchemyContentMediaQueryRepository(session)),
    )
