from dataclasses import replace
from src.modules.channels.application.batch_export.port.jobs import BatchExportJobs
from src.modules.channels.application.batch_export.query.get_batch_export.dto import (
    BatchExportDetailDTO,
)
from src.modules.channels.application.batch_export.port.queries import (
    BatchExportQueries,
)
from src.modules.channels.application.batch_export.query.get_batch_export.query import (
    GetBatchExportQuery,
)
from src.modules.channels.domain.error import (
    ChannelsValidationError,
    ChannelsNotFoundError,
)
from src.modules.channels.application.batch_export.port.feed_links import (
    BatchExportFeedLinks,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class GetBatchExportHandler:
    """Читает результат пакета без восстановления Domain и внешней сети."""

    def __init__(
        self,
        queries: BatchExportQueries,
        jobs: BatchExportJobs,
        links: BatchExportFeedLinks,
        clock: ClockPort,
    ) -> None:
        """Принимает специализированный query port."""
        self.queries, self.jobs = queries, jobs
        self.links, self.clock = links, clock

    async def execute(self, query: GetBatchExportQuery) -> BatchExportDetailDTO:
        """Ограничивает страницу и не раскрывает приватные данные плагина."""
        if not 1 <= query.limit <= 100 or query.offset < 0:
            raise ChannelsValidationError("invalid_batch_export_page")
        result = await self.queries.detail(query.run_id, query.offset, query.limit)
        try:
            feed = await self.queries.feed(query.run_id)
        except ChannelsNotFoundError:
            feed = None
        if (
            feed is not None
            and feed.expires_at > self.clock.now()
            and (await self.links.availability(query.tenant_id)).feed_available
        ):
            result = replace(
                result,
                feed_url=await self.links.url(
                    query.tenant_id, query.run_id, feed.expires_at
                ),
                feed_expires_at=feed.expires_at,
            )
        job_id = await self.queries.current_job(query.run_id)
        if job_id is not None and not await self.jobs.is_recoverable(
            query.tenant_id, job_id
        ):
            result = replace(result, run=replace(result.run, interrupted=True))
        return result
