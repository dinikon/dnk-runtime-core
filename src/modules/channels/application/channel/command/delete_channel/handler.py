from src.modules.channels.application.stock_sync.ports import StockJobsPort
from src.modules.channels.application.content_delivery.port.jobs import (
    ContentDeliveryJobsPort,
)
from collections.abc import Callable
from datetime import datetime

from src.modules.channels.application.sync_run.service import SyncRuns
from src.modules.channels.application.channel.command.delete_channel.command import (
    DeleteChannelCommand,
)
from src.modules.channels.application.channel.port.jobs import VerificationJobs
from src.modules.channels.domain.channel.error import ChannelNotFoundError
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class DeleteChannelHandler:
    """Удаляет локальный агрегат и отменяет его активные задания."""

    def __init__(
        self,
        repository: ChannelRepositoryProtocol,
        jobs: VerificationJobs,
        clock: Callable[[], datetime],
        *,
        sync_runs: SyncRuns | None = None,
        stock_jobs: StockJobsPort | None = None,
        content_jobs: ContentDeliveryJobsPort | None = None,
    ) -> None:
        """Принимает порты общей транзакции."""
        self.repository, self.jobs, self.clock = repository, jobs, clock
        self.sync_runs = sync_runs
        self.stock_jobs = stock_jobs
        self.content_jobs = content_jobs

    async def execute(self, command: DeleteChannelCommand) -> None:
        """Сначала блокирует Channel, затем задания; внешний API не вызывается."""
        channel = await self.repository.get(
            EntityIdVO.from_value(command.channel_id), for_update=True
        )
        if channel is None:
            raise ChannelNotFoundError("Канал не найден.")
        channel.require_revision(command.expected_revision)
        if self.sync_runs is not None:
            await self.sync_runs.cancel(
                channel=channel, tenant_id=command.tenant_id, reason="channel_deleted"
            )
        await self.jobs.cancel(command.tenant_id, channel.id.uuid, self.clock())
        if self.stock_jobs is not None:
            await self.stock_jobs.cancel_channel(
                tenant_id=command.tenant_id,
                channel_id=channel.id.uuid,
                now=self.clock(),
            )
        if self.content_jobs is not None:
            await self.content_jobs.cancel_channel(
                tenant_id=command.tenant_id,
                channel_id=channel.id.uuid,
                now=self.clock(),
            )
        await self.repository.delete(channel.id)
