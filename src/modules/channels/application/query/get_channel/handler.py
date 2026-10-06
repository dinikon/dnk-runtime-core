from src.modules.channels.application.port.query_repository import (
    ChannelQueryRepositoryProtocol,
)
from src.modules.channels.domain.error import ChannelNotFoundError
from src.modules.channels.application.query.get_channel.query import GetChannelQuery


class GetChannelHandler:
    def __init__(self, repository: ChannelQueryRepositoryProtocol):
        self.repository = repository

    async def execute(self, query: GetChannelQuery):
        result = await self.repository.get(query.channel_id)
        if result is None:
            raise ChannelNotFoundError("Channel not found.")
        return result
