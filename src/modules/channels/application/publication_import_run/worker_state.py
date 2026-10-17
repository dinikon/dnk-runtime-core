from uuid import UUID
from src.modules.channels.domain.publication_import_run.value_object.identifier import (
    PublicationImportRunIdVO,
)
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO
from src.modules.channels.domain.publication_import_run.aggregate import (
    PublicationImportRun,
)
from src.modules.channels.domain.publication_import_run.repository import (
    PublicationImportRunRepositoryProtocol,
)
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class PublicationImportState:
    """Координирует блокировки и защиту от устаревших фоновых заданий."""

    def __init__(
        self,
        channels: ChannelRepositoryProtocol,
        runs: PublicationImportRunRepositoryProtocol,
        jobs: ScheduledJobRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Принимает порты одной короткой транзакции фонового шага."""
        self.channels, self.runs, self.jobs, self.clock = channels, runs, jobs, clock

    async def load(
        self,
        *,
        tenant_id: UUID,
        channel_id: UUID,
        run_id: UUID,
        job_id: UUID,
        lock_token: str,
    ) -> tuple[Channel, PublicationImportRun] | None:
        """Проверяет lease, канал, ревизию подключения и ожидаемое задание."""
        if not await self.jobs.owns_current_lease(
            job_id=job_id, tenant_id=tenant_id, lock_token=lock_token, for_update=True
        ):
            return None
        channel = await self.channels.get_for_update(ChannelIdVO.from_value(channel_id))
        if channel is None:
            return None
        run = await self.runs.get(PublicationImportRunIdVO.from_value(run_id))
        if (
            run is None
            or run.channel_id.uuid != channel_id
            or not run.active
            or run.job_id.uuid != job_id
        ):
            return None
        if (
            channel.connection_revision != run.connection_revision
            or not channel.is_active
        ):
            await self.runs.save(
                run.finish(
                    error_code=(
                        "connection_changed"
                        if channel.connection_revision != run.connection_revision
                        else "channel_inactive"
                    ),
                    now=self.clock.now(),
                )
            )
            return None
        return channel, run
