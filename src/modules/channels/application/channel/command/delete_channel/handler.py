from src.modules.channels.application.channel.command.delete_channel.command import (
    DeleteChannelCommand,
)
from src.modules.channels.domain.channel.error import ChannelNotFoundError
from src.modules.channels.domain.channel.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO


class DeleteChannelHandler:
    """Координирует удаление канала вместе с credentials в общей транзакции."""

    def __init__(self, repository: ChannelRepositoryProtocol) -> None:
        """Принимает порт сценария из внешней сборки зависимостей."""
        self._repository = repository

    async def execute(self, command: DeleteChannelCommand) -> None:
        """Удаляет канал либо сообщает об отсутствии, оставляя commit внешнему UoW."""
        if not await self._repository.delete(
            ChannelIdVO.from_value(command.channel_id)
        ):
            raise ChannelNotFoundError("Channel not found.")
