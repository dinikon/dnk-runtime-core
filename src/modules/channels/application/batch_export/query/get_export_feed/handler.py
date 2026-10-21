from src.modules.channels.application.batch_export.port.queries import (
    BatchExportQueries,
)
from src.modules.channels.application.batch_export.query.get_export_feed.query import (
    GetExportFeedQuery,
)
from src.modules.channels.application.batch_export.query.get_export_feed.dto import (
    GetExportFeedResultDTO,
)
from src.modules.files.application.artifact.facade import ArtifactFilesFacadeProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.domain.error import ChannelsNotFoundError


class GetExportFeedHandler:
    """Читает только подписанный снимок, не создаёт фид из текущего Catalog."""

    def __init__(
        self,
        queries: BatchExportQueries,
        files: ArtifactFilesFacadeProtocol,
        clock: ClockPort,
    ) -> None:
        """Принимает query port, публичный Files facade и часы."""
        self.queries, self.files, self.clock = queries, files, clock

    async def execute(self, query: GetExportFeedQuery) -> GetExportFeedResultDTO:
        """Проверяет срок и размер до открытия сетевого потока."""
        feed = await self.queries.feed(query.run_id)
        if feed.expires_at <= self.clock.now():
            raise ChannelsNotFoundError("export_feed_not_found")
        location = await self.files.location(query.tenant_id, feed.file_id)
        if location.size_bytes != feed.size:
            raise ChannelsNotFoundError("export_feed_not_found")
        return GetExportFeedResultDTO(location, feed.digest)
