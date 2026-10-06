from src.modules.channels.application.port.query_repository import (
    ChannelQueryRepositoryProtocol,
)
from src.modules.channels.domain.error import ChannelNotFoundError
from src.modules.channels.application.query.list_channels.query import ListChannelsQuery


class ListChannelsHandler:
    def __init__(self, repository: ChannelQueryRepositoryProtocol):
        self.repository = repository

    async def execute(self, query: ListChannelsQuery):
        return await self.repository.list_all()
