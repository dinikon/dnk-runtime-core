from src.modules.channels.application.batch_export.command.prepare_export_artifact_page.handler import (
    PrepareExportArtifactPageHandler,
)
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import dnk_config
from src.modules.channels.application.batch_export.access import BatchExportAccess
from src.modules.channels.application.batch_export.command.start_batch_export.handler import (
    StartBatchExportHandler,
)
from src.modules.channels.application.batch_export.command.prepare_batch_export_step.handler import (
    PrepareBatchExportStepHandler,
)
from src.modules.channels.application.batch_export.command.apply_batch_export_step.handler import (
    ApplyBatchExportStepHandler,
)
from src.modules.channels.application.batch_export.command.resume_batch_export.handler import (
    ResumeBatchExportHandler,
)
from src.modules.channels.application.batch_export.query.get_batch_export.handler import (
    GetBatchExportHandler,
)
from src.modules.channels.application.batch_export.query.get_batch_export_overview.handler import (
    GetBatchExportOverviewHandler,
)
from src.modules.channels.application.export_schedule.command.update_export_schedule.handler import (
    UpdateExportScheduleHandler,
)
from src.modules.channels.application.export_schedule.command.execute_daily_export.handler import (
    ExecuteDailyExportHandler,
)
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.infrastructure.batch_export.persistence.repository import (
    SqlAlchemyBatchExportRepository,
)
from src.modules.channels.infrastructure.batch_export.persistence.queries import (
    SqlAlchemyBatchExportQueries,
)
from src.modules.channels.infrastructure.export_schedule.persistence.repository import (
    SqlAlchemyExportScheduleRepository,
)
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.infrastructure.content_update.adapter.catalog import (
    CatalogContentAdapter,
)
from src.modules.channels.infrastructure.batch_export.feed_links import ExportFeedLinks
from src.modules.channels.infrastructure.batch_export.tenant_feed_links import (
    TenantExportFeedLinks,
)
from src.modules.tenancy.infrastructure.tenant_domain.public_hosts import (
    SqlAlchemyTenantPublicHosts,
)
from src.modules.channels.infrastructure.jobs import ScheduledChannelsJobs
from src.modules.catalog.infrastructure.catalog_item.assembly import (
    build_catalog_items_facade,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from src.modules.shared.presentation.jobs.management import (
    build_schedule_scheduled_job_use_case,
    build_scheduled_job_repository,
)


@dataclass(frozen=True, slots=True)
class BatchExportHandlers:
    """Внешняя сборка конкретных сценариев на общей tenant-сессии."""

    access: BatchExportAccess
    start: StartBatchExportHandler
    prepare: PrepareBatchExportStepHandler
    apply: ApplyBatchExportStepHandler
    resume: ResumeBatchExportHandler
    get: GetBatchExportHandler
    overview: GetBatchExportOverviewHandler
    update_schedule: UpdateExportScheduleHandler
    daily: ExecuteDailyExportHandler
    artifact_page: PrepareExportArtifactPageHandler


def get_export_feed_links() -> ExportFeedLinks:
    """Собирает подпись файла без общего deployment URL."""
    return ExportFeedLinks(
        dnk_config.CHANNELS.credentials_encryption_key.get_secret_value(),
    )


def build_batch_export_handlers(
    session: AsyncSession,
    registry: PluginRegistryProtocol,
) -> BatchExportHandlers:
    """Переиспользует публичный фасад Catalog, shared Jobs и существующий канал."""
    clock = UtcClock()
    jobs = ScheduledChannelsJobs(
        build_schedule_scheduled_job_use_case(session=session),
        build_scheduled_job_repository(session),
    )
    queries = SqlAlchemyBatchExportQueries(session)
    links = TenantExportFeedLinks(
        SqlAlchemyTenantPublicHosts(session), get_export_feed_links()
    )
    access = BatchExportAccess(
        SqlAlchemyBatchExportRepository(session),
        SqlAlchemyChannelRepository(session),
        queries,
        SqlAlchemyExportScheduleRepository(session),
        CatalogContentAdapter(
            build_catalog_items_facade(session, clock, UUID7Generator())
        ),
        registry,
        jobs,
        clock,
        feed_links=links,
    )
    return BatchExportHandlers(
        access,
        StartBatchExportHandler(access),
        PrepareBatchExportStepHandler(access),
        ApplyBatchExportStepHandler(access),
        ResumeBatchExportHandler(access),
        GetBatchExportHandler(queries, jobs, links, clock),
        GetBatchExportOverviewHandler(queries, registry, feed_links=links),
        UpdateExportScheduleHandler(access),
        ExecuteDailyExportHandler(access),
        PrepareExportArtifactPageHandler(access),
    )
