from src.modules.channels.application.publication_import.query.get_publication_import_image.handler import (
    GetPublicationImportImageHandler,
)
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.application.publication_import.access import (
    PublicationImportAccess,
)
from src.modules.channels.application.publication_import.command.start_publication_import.handler import (
    StartPublicationImportHandler,
)
from src.modules.channels.application.publication_import.command.prepare_publication_import_step.handler import (
    PreparePublicationImportStepHandler,
)
from src.modules.channels.application.publication_import.command.apply_publication_import_step.handler import (
    ApplyPublicationImportStepHandler,
)
from src.modules.channels.application.publication_import.command.retry_publication_import.handler import (
    RetryPublicationImportHandler,
)
from src.modules.channels.application.publication_import.command.cancel_publication_import.handler import (
    CancelPublicationImportHandler,
)
from src.modules.channels.application.publication_import.command.cleanup_publication_import.handler import (
    CleanupPublicationImportHandler,
)
from src.modules.channels.application.publication_import.query.get_publication_import.handler import (
    GetPublicationImportHandler,
)
from src.modules.channels.infrastructure.publication_import.persistence.repository import (
    SqlAlchemyPublicationImportRepository,
)
from src.modules.channels.infrastructure.publication_import.persistence.query_repository import (
    SqlAlchemyPublicationImportQueries,
)
from src.modules.channels.infrastructure.publication_import.adapter.files import (
    FilesPublicationImportAdapter,
)
from src.modules.channels.infrastructure.product_representation.persistence.publications import (
    SqlAlchemyPublicationCatalogSource,
)
from src.modules.channels.infrastructure.product_representation.persistence.binding_queries import (
    SqlAlchemyBindingQueries,
)
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.infrastructure.jobs import ScheduledChannelsJobs
from src.modules.catalog.infrastructure.catalog_item.files import FilesCatalogImages
from src.modules.catalog.infrastructure.catalog_item.image_usage import (
    SqlAlchemyCatalogImageUsage,
)
from src.modules.catalog.application.catalog_item.query.find_used_image_files.handler import (
    FindUsedImageFilesHandler,
)
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.files.application.port.storage import StorageResolverProtocol
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.presentation.jobs.management import (
    build_schedule_scheduled_job_use_case,
    build_scheduled_job_repository,
)


@dataclass(frozen=True, slots=True)
class PublicationImportHandlers:
    """Внешняя сборка конкретных сценариев одной tenant-транзакции."""

    start: StartPublicationImportHandler
    prepare: PreparePublicationImportStepHandler
    apply: ApplyPublicationImportStepHandler
    retry: RetryPublicationImportHandler
    cancel: CancelPublicationImportHandler
    cleanup: CleanupPublicationImportHandler
    get: GetPublicationImportHandler
    image: GetPublicationImportImageHandler


def build_publication_import_handlers(
    session: AsyncSession,
    registry: PluginRegistryProtocol,
    storage: StorageResolverProtocol | None = None,
) -> PublicationImportHandlers:
    """Собирает порты на одном UoW, оставляя внешнее чтение worker-границе."""
    clock = UtcClock()
    imports = SqlAlchemyPublicationImportRepository(session)
    sources = SqlAlchemyPublicationCatalogSource(session)
    channels = SqlAlchemyChannelRepository(session)
    access = PublicationImportAccess(imports, sources)
    jobs = ScheduledChannelsJobs(
        build_schedule_scheduled_job_use_case(session=session),
        build_scheduled_job_repository(session),
    )
    files = build_files_handlers(session, storage)
    images = FilesCatalogImages(files.upload, files.content, files.lock_ready)
    media = FilesPublicationImportAdapter(
        images,
        FindUsedImageFilesHandler(SqlAlchemyCatalogImageUsage(session)),
        files.lock_ready,
        files.trash_file,
    )
    return PublicationImportHandlers(
        StartPublicationImportHandler(
            imports,
            sources,
            channels,
            SqlAlchemyBindingQueries(session),
            registry,
            jobs,
            clock,
        ),
        PreparePublicationImportStepHandler(access, imports, channels, registry, clock),
        ApplyPublicationImportStepHandler(
            access, imports, channels, jobs, clock, media
        ),
        RetryPublicationImportHandler(access, imports, jobs, clock),
        CancelPublicationImportHandler(access, imports, jobs, clock),
        CleanupPublicationImportHandler(access, imports, media, clock),
        GetPublicationImportHandler(
            SqlAlchemyPublicationImportQueries(session), clock, jobs
        ),
        GetPublicationImportImageHandler(
            SqlAlchemyPublicationImportQueries(session), media, clock
        ),
    )
