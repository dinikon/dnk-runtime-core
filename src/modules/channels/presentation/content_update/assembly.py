from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.application.content_update.access import ContentUpdateAccess
from src.modules.channels.infrastructure.content_update.persistence.repository import (
    SqlAlchemyContentUpdateRepository,
)
from src.modules.channels.infrastructure.content_update.persistence.query_repository import (
    SqlAlchemyContentUpdateQueries,
)
from src.modules.channels.infrastructure.content_update.adapter.catalog import (
    CatalogContentAdapter,
)
from src.modules.channels.infrastructure.channel.persistence.repository import (
    SqlAlchemyChannelRepository,
)
from src.modules.channels.infrastructure.product_representation.persistence.binding_queries import (
    SqlAlchemyBindingQueries,
)
from src.modules.channels.infrastructure.product_representation.persistence.publications import (
    SqlAlchemyPublicationCatalogSource,
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
from src.modules.channels.application.content_update.command.start_content_update.handler import (
    StartContentUpdateHandler,
)
from src.modules.channels.application.content_update.command.confirm_content_update.handler import (
    ConfirmContentUpdateHandler,
)
from src.modules.channels.application.content_update.command.retry_content_update.handler import (
    RetryContentUpdateHandler,
)
from src.modules.channels.application.content_update.query.get_content_update.handler import (
    GetContentUpdateHandler,
)
from src.modules.channels.application.content_update.query.list_content_updates.handler import (
    ListContentUpdatesHandler,
)
from src.modules.channels.application.content_update.command.prepare_content_update_step.handler import (
    PrepareContentUpdateStepHandler,
)
from src.modules.channels.application.content_update.command.apply_content_update_step.handler import (
    ApplyContentUpdateStepHandler,
)


@dataclass(frozen=True, slots=True)
class ContentUpdateHandlers:
    """Собирает конкретные исходящие сценарии на общей tenant-сессии."""

    start: StartContentUpdateHandler
    confirm: ConfirmContentUpdateHandler
    retry: RetryContentUpdateHandler
    prepare: PrepareContentUpdateStepHandler
    apply: ApplyContentUpdateStepHandler
    get: GetContentUpdateHandler
    listing: ListContentUpdatesHandler


def build_content_update_handlers(
    session: AsyncSession, registry: PluginRegistryProtocol
) -> ContentUpdateHandlers:
    """Переиспользует фасад Catalog и durable jobs без новой инфраструктуры доставки."""
    clock = UtcClock()
    jobs = ScheduledChannelsJobs(
        build_schedule_scheduled_job_use_case(session=session),
        build_scheduled_job_repository(session),
    )
    queries = SqlAlchemyContentUpdateQueries(session)
    access = ContentUpdateAccess(
        SqlAlchemyContentUpdateRepository(session),
        queries,
        SqlAlchemyChannelRepository(session),
        SqlAlchemyBindingQueries(session),
        SqlAlchemyPublicationCatalogSource(session),
        CatalogContentAdapter(
            build_catalog_items_facade(session, clock, UUID7Generator())
        ),
        registry,
    )
    return ContentUpdateHandlers(
        StartContentUpdateHandler(access, jobs, clock),
        ConfirmContentUpdateHandler(access, jobs, clock),
        RetryContentUpdateHandler(access, jobs, jobs, clock),
        PrepareContentUpdateStepHandler(access, clock),
        ApplyContentUpdateStepHandler(access, jobs, clock),
        GetContentUpdateHandler(queries, jobs),
        ListContentUpdatesHandler(queries),
    )
