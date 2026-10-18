from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.channels.application.channel.command.update_channel_policy.command import (
    UpdateChannelPolicyCommand,
)
from src.modules.channels.application.channel.command.update_channel_policy.dto import (
    UpdateChannelPolicyResultDTO,
)


class UpdateChannelPolicyHandler:
    """Координирует update_channel_policy через доменные методы Channel."""

    def __init__(self, channels: ChannelRepositoryProtocol, clock: ClockPort) -> None:
        """Принимает только зависимости, необходимые этому сценарию."""
        self.channels = channels
        self.clock = clock

    async def execute(
        self, command: UpdateChannelPolicyCommand
    ) -> UpdateChannelPolicyResultDTO:
        """Проверяет версию и сохраняет разрешённый переход без commit."""
        channel = await self.channels.get(EntityIdVO.from_value(command.channel_id))
        channel.ensure_revision(command.revision)
        channel.update_policy(
            command.name if command.name is not None else channel.name,
            (
                command.is_enabled
                if command.is_enabled is not None
                else channel.is_enabled
            ),
            EntityIdVO.from_value(command.actor_id),
            self.clock.now(),
        )
        await self.channels.save(channel)
        return UpdateChannelPolicyResultDTO(channel.id.uuid, channel.revision)
