from typing import Protocol
from src.modules.channels.application.channel.query.get_channel.query import (
    GetChannelQuery,
)
from src.modules.channels.application.channel.query.get_channel.dto import (
    GetChannelResultDTO,
)
from src.modules.channels.application.channel.query.list_channels.query import (
    ListChannelsQuery,
)
from src.modules.channels.application.channel.query.list_channels.dto import (
    ListChannelsResultDTO,
)
from src.modules.channels.application.channel.query.get_connection.query import (
    GetConnectionQuery,
)
from src.modules.channels.application.channel.query.get_connection.dto import (
    GetConnectionResultDTO,
)


class ChannelQueryRepositoryProtocol(Protocol):
    """Определяет чтение готовых DTO без ORM во внутренних слоях."""

    async def get_channel(self, query: GetChannelQuery) -> GetChannelResultDTO:
        """Читает проекцию get_channel в текущей tenant-схеме."""
        ...

    async def list_channels(self, query: ListChannelsQuery) -> ListChannelsResultDTO:
        """Читает проекцию list_channels в текущей tenant-схеме."""
        ...

    async def get_connection(self, query: GetConnectionQuery) -> GetConnectionResultDTO:
        """Читает проекцию get_connection в текущей tenant-схеме."""
        ...
