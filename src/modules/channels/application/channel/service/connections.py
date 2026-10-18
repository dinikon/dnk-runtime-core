from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from uuid import UUID, uuid5
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.application.port.jobs import ChannelsJobsProtocol
from src.modules.channels.application.sync_run.service.initialization import (
    InitializationService,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class ConnectionWorkflow:
    """Координирует смену generation и атомарное планирование проверки."""

    def __init__(
        self,
        channels: ChannelRepositoryProtocol,
        jobs: ChannelsJobsProtocol,
        initialization: InitializationService,
        clock: ClockPort,
    ) -> None:
        """Использует порты одной tenant-транзакции."""
        self.channels, self.jobs, self.initialization, self.clock = (
            channels,
            jobs,
            initialization,
            clock,
        )

    async def verify(self, tenant_id: UUID, channel: Channel, actor_id: UUID) -> UUID:
        """Отменяет старое чтение и ставит проверку с устойчивым job ID."""
        await self.initialization.cancel_active(channel)
        connection = channel.require_connection()
        job_id = uuid5(connection.id.uuid, f"verify:{connection.generation + 1}")
        channel.request_verification(
            EntityIdVO.from_value(job_id),
            EntityIdVO.from_value(actor_id),
            self.clock.now(),
        )
        await self.channels.save(channel)
        await self.jobs.verification(
            tenant_id,
            channel.id.uuid,
            job_id,
            connection.generation,
            actor_id,
            self.clock.now(),
        )
        return job_id
