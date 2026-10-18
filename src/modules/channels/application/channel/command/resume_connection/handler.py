from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.application.channel.service.connections import (
    ConnectionWorkflow,
)
from src.modules.channels.application.sync_run.service.initialization import (
    InitializationService,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.channel.command.resume_connection.command import (
    ResumeConnectionCommand,
)
from uuid import UUID, uuid5
from src.modules.channels.domain.channel.aggregate import Channel


class ResumeConnectionHandler:
    """Координирует resume_connection через доменные методы Channel."""

    def __init__(
        self,
        channels: ChannelRepositoryProtocol,
        workflow: ConnectionWorkflow,
        initialization: InitializationService,
        clock: ClockPort,
    ) -> None:
        """Принимает порты и сервисы одной внешней транзакции."""
        self.channels, self.workflow, self.initialization, self.clock = (
            channels,
            workflow,
            initialization,
            clock,
        )

    async def execute(self, command: ResumeConnectionCommand) -> None:
        """Проверяет версию и сохраняет разрешённый переход без commit."""
        channel = await self.channels.get(EntityIdVO.from_value(command.channel_id))
        channel.ensure_revision(command.revision)
        channel.resume_connection(
            EntityIdVO.from_value(command.actor_id), self.clock.now()
        )
        await self.channels.save(channel)
        if channel.require_connection().verification_status == "verified":
            await self.initialization.start(
                command.tenant_id,
                channel,
                command.actor_id,
                self.workflow_uuid(channel),
                automatic=True,
            )
        else:
            await self.workflow.verify(command.tenant_id, channel, command.actor_id)

    def workflow_uuid(self, channel: Channel) -> UUID:
        """Получает устойчивую identity автоматического возобновления."""
        return uuid5(channel.id.uuid, f"resume:{channel.revision}")
