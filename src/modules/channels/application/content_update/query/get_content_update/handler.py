from dataclasses import replace
from uuid import uuid5
from src.modules.channels.application.content_update.port.queries import (
    ContentUpdateQueries,
)
from src.modules.channels.application.port.jobs import ChannelsJobsProtocol
from src.modules.channels.application.content_update.query.get_content_update.query import (
    GetContentUpdateQuery,
)
from src.modules.channels.application.content_update.query.get_content_update.dto import (
    GetContentUpdateResultDTO,
)


class GetContentUpdateHandler:
    """Читает готовую проекцию; GET не восстанавливает корень и не изменяет данные."""

    def __init__(
        self, queries: ContentUpdateQueries, jobs: ChannelsJobsProtocol
    ) -> None:
        """Принимает read порты операций и существующей очереди."""
        self.queries, self.jobs = queries, jobs

    async def execute(self, query: GetContentUpdateQuery) -> GetContentUpdateResultDTO:
        """Показывает прерванный job как восстанавливаемое состояние без скрытой записи."""
        result = await self.queries.get(query.run_id, query.actor_id)
        if result.status in ("preparing", "queued", "running"):
            active = await self.jobs.is_recoverable(
                query.tenant_id, uuid5(result.id, "content:" + str(result.sequence))
            )
            return replace(result, interrupted=not active)
        return result
