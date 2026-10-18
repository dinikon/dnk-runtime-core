from src.modules.channels.application.channel.query.list_channels.query import (
    ListChannelsQuery,
)
from src.modules.channels.application.channel.query.list_channels.dto import (
    ListChannelsResultDTO,
)
from src.modules.channels.domain.error import ChannelsValidationError
from src.modules.channels.application.channel.port.query_repository import (
    ChannelQueryRepositoryProtocol,
)


class ListChannelsHandler:
    """Выполняет чтение list_channels без write repository и восстановления агрегатов."""

    def __init__(self, repository: ChannelQueryRepositoryProtocol) -> None:
        """Принимает порт готовых проекций либо manifest registry."""
        self.repository = repository

    async def execute(self, query: ListChannelsQuery) -> ListChannelsResultDTO:
        """Возвращает конкретный DTO сценария чтения."""
        if query.offset < 0 or not 1 <= query.limit <= 100:
            raise ChannelsValidationError("invalid_pagination")
        return await self.repository.list_channels(query)
