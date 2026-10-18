from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.application.channel.service.connections import (
    ConnectionWorkflow,
)
from src.modules.channels.application.channel.command.verify_connection.command import (
    VerifyConnectionCommand,
)
from src.modules.channels.application.channel.command.verify_connection.dto import (
    VerifyConnectionResultDTO,
)


class VerifyConnectionHandler:
    """Координирует verify_connection через доменные методы Channel."""

    def __init__(
        self, channels: ChannelRepositoryProtocol, workflow: ConnectionWorkflow
    ) -> None:
        """Принимает только зависимости, необходимые этому сценарию."""
        self.channels = channels
        self.workflow = workflow

    async def execute(
        self, command: VerifyConnectionCommand
    ) -> VerifyConnectionResultDTO:
        """Проверяет версию и сохраняет разрешённый переход без commit."""
        channel = await self.channels.get(EntityIdVO.from_value(command.channel_id))
        channel.ensure_revision(command.revision)
        job_id = await self.workflow.verify(
            command.tenant_id, channel, command.actor_id
        )
        return VerifyConnectionResultDTO(channel.id.uuid, channel.revision, job_id)
