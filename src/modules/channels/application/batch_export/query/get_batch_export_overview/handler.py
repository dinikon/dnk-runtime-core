from src.modules.channels.application.batch_export.port.queries import (
    BatchExportQueries,
)
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.channels.application.batch_export.query.get_batch_export_overview.query import (
    GetBatchExportOverviewQuery,
)
from src.modules.channels.application.batch_export.query.get_batch_export_overview.dto import (
    GetBatchExportOverviewResultDTO,
)
from src.modules.channels.domain.error import ChannelsUnavailableError
from src.modules.channels.application.batch_export.port.feed_links import (
    BatchExportFeedLinks,
)


class GetBatchExportOverviewHandler:
    """Читает специализированные проекции без Domain roots и внешней сети."""

    def __init__(
        self,
        queries: BatchExportQueries,
        registry: PluginRegistryProtocol,
        *,
        feed_links: BatchExportFeedLinks,
    ) -> None:
        """Принимает query port, manifest registry и порт адресов tenant."""
        self.queries, self.registry, self.links = (
            queries,
            registry,
            feed_links,
        )

    async def execute(
        self, query: GetBatchExportOverviewQuery
    ) -> GetBatchExportOverviewResultDTO:
        """Показывает policy и историю без восстановления или изменения агрегатов."""
        scope = await self.queries.channel_scope(query.channel_id)
        if (
            "batch_content_export"
            not in self.registry.manifest(scope.platform_kind).capabilities
        ):
            raise ChannelsUnavailableError("batch_export_unsupported")
        bound, enabled = await self.queries.eligibility(scope.connection_id)
        availability = await self.links.availability(query.tenant_id)
        return GetBatchExportOverviewResultDTO(
            scope.outbound_enabled,
            availability.delivery_configured,
            bound,
            enabled,
            await self.queries.schedule(query.channel_id),
            await self.queries.recent(query.channel_id),
            availability.feed_available,
        )
