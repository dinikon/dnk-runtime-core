"""Чтение сохранённого прогресса без обращения к площадке."""

from dataclasses import replace

from src.modules.channels.application.sync_run.query.get_latest_sync_run.query import (
    GetLatestSyncRunQuery,
)
from src.modules.channels.application.sync_run.query.get_latest_sync_run.dto import (
    GetLatestSyncRunResultDTO,
)
from src.modules.channels.application.sync_run.port.query_repository import (
    SyncRunQueryRepository,
)
from src.modules.channels.application.sync_run.port.jobs import PublicationSyncJobs
from src.modules.channels.application.external_publication.port.query_repository import (
    PublicationQueryRepository,
)
from src.modules.channels.domain.channel.error import ChannelNotFoundError


class GetLatestSyncRunHandler:
    """Дополняет read-проекцию признаком потерянного задания."""

    def __init__(
        self,
        runs: SyncRunQueryRepository,
        publications: PublicationQueryRepository,
        jobs: PublicationSyncJobs,
    ) -> None:
        """Получает порты чтения одной внешней транзакции."""
        self.runs, self.publications, self.jobs = runs, publications, jobs

    async def execute(self, query: GetLatestSyncRunQuery) -> GetLatestSyncRunResultDTO:
        """Возвращает DTO исключительно выбранного канала."""
        connection = await self.publications.connection(query.channel_id)
        if connection is None:
            raise ChannelNotFoundError("Канал не найден.")
        row = await self.runs.latest(connection.id)
        if row is not None and row.status in {"queued", "running"}:
            row = replace(
                row,
                recovery_required=not await self.jobs.active(
                    query.tenant_id, row.current_job_id
                ),
            )
        return GetLatestSyncRunResultDTO(row)
