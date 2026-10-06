from src.modules.channels.application.command.delete_channel.command import (
    DeleteChannelCommand,
)
from src.modules.channels.domain.error import ChannelNotFoundError
from src.modules.channels.domain.repository import ChannelRepositoryProtocol
from src.modules.channels.domain.value_object.identifier import ChannelIdVO


class DeleteChannelHandler:
    def __init__(self, repository: ChannelRepositoryProtocol):
        self.repository = repository

    async def execute(self, command: DeleteChannelCommand):
        if not await self.repository.delete(ChannelIdVO.from_value(command.channel_id)):
            raise ChannelNotFoundError("Channel not found.")
