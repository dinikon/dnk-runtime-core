from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.application.sync_run.service.initialization import (
    InitializationService,
)
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.channel.command.archive_channel.command import (
    ArchiveChannelCommand,
)


class ArchiveChannelHandler:
    """Координирует archive_channel через доменные методы Channel."""

    def __init__(
        self,
        channels: ChannelRepositoryProtocol,
        initialization: InitializationService,
        clock: ClockPort,
    ) -> None:
        """Принимает только зависимости, необходимые этому сценарию."""
        self.channels = channels
        self.initialization = initialization
        self.clock = clock

    async def execute(self, command: ArchiveChannelCommand) -> None:
        """Проверяет версию и сохраняет разрешённый переход без commit."""
        channel = await self.channels.get(EntityIdVO.from_value(command.channel_id))
        channel.ensure_revision(command.revision)
        channel.archive(EntityIdVO.from_value(command.actor_id), self.clock.now())
        await self.initialization.cancel_active(channel)
        await self.channels.save(channel)
