from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.application.channel.command.create_channel.command import (
    CreateChannelCommand,
)
from src.modules.channels.application.channel.command.create_channel.dto import (
    CreateChannelResultDTO,
)
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.channel.aggregate import Channel
from src.modules.channels.application.port.plugin_registry import PluginRegistryProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.shared.application.uuid.uuid_port import UUIdGeneratorProtocol


class CreateChannelHandler:
    """Создаёт канал только зарегистрированной платформы."""

    def __init__(
        self,
        channels: ChannelRepositoryProtocol,
        registry: PluginRegistryProtocol,
        clock: ClockPort,
        identifiers: UUIdGeneratorProtocol,
    ) -> None:
        """Принимает repository, registry и источники времени/ID."""
        self.channels, self.registry, self.clock, self.identifiers = (
            channels,
            registry,
            clock,
            identifiers,
        )

    async def execute(self, command: CreateChannelCommand) -> CreateChannelResultDTO:
        """Создаёт источник с is_enabled=false независимо от возможностей платформы."""
        self.registry.manifest(command.platform_kind)
        channel = Channel.create(
            EntityIdVO.from_value(self.identifiers.new()),
            command.name,
            command.platform_kind,
            EntityIdVO.from_value(command.actor_id),
            self.clock.now(),
        )
        await self.channels.add(channel)
        return CreateChannelResultDTO(
            channel.id.uuid, channel.revision, channel.is_enabled
        )
