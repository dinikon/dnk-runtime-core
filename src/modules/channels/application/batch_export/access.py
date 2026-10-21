from uuid import UUID
from src.modules.channels.domain.batch_export.repository import BatchExportRepository
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.batch_export.aggregate import BatchExportRun
from src.modules.channels.application.batch_export.port.queries import (
    BatchExportQueries,
)
from src.modules.channels.application.batch_export.port.jobs import BatchExportJobs
from src.modules.channels.application.content_update.port.catalog_content import (
    CatalogContentFacade,
)
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.domain.export_schedule.repository import (
    ExportScheduleRepository,
)
from src.modules.channels.domain.error import ChannelsUnavailableError
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.application.batch_export.port.feed_links import (
    BatchExportFeedLinks,
)


class BatchExportAccess:
    """Объединяет порты сценариев без SQL, сетевых клиентов и вызовов handlers."""

    def __init__(
        self,
        runs: BatchExportRepository,
        channels: ChannelRepositoryProtocol,
        queries: BatchExportQueries,
        schedules: ExportScheduleRepository,
        catalog: CatalogContentFacade,
        registry: PluginRegistryProtocol,
        jobs: BatchExportJobs,
        clock: ClockPort,
        *,
        feed_links: BatchExportFeedLinks,
    ) -> None:
        """Получает зависимости одной внешней транзакции."""
        self.runs, self.channels, self.queries, self.schedules = (
            runs,
            channels,
            queries,
            schedules,
        )
        self.catalog, self.registry, self.jobs, self.clock = (
            catalog,
            registry,
            jobs,
            clock,
        )
        self.feed_links = feed_links

    def require_capability(self, channel: Channel) -> None:
        """Отклоняет неподдержанную платформу по manifest."""
        if (
            "batch_content_export"
            not in self.registry.manifest(channel.platform_kind).capabilities
        ):
            raise ChannelsUnavailableError("batch_export_unsupported")

    async def locked(self, run_id: UUID) -> tuple[BatchExportRun, Channel]:
        """Блокирует сначала Channel, затем пакет, как при ручном старте."""
        channel = await self.channels.get(EntityIdVO(await self.queries.scope(run_id)))
        return await self.runs.get(run_id), channel
