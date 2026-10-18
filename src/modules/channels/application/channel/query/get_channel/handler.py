from src.modules.channels.application.channel.query.get_channel.query import (
    GetChannelQuery,
)
from src.modules.channels.application.channel.query.get_channel.dto import (
    GetChannelResultDTO,
)
from src.modules.channels.application.channel.port.query_repository import (
    ChannelQueryRepositoryProtocol,
)


class GetChannelHandler:
    """Выполняет чтение get_channel без write repository и восстановления агрегатов."""

    def __init__(self, repository: ChannelQueryRepositoryProtocol) -> None:
        """Принимает порт готовых проекций либо manifest registry."""
        self.repository = repository

    async def execute(self, query: GetChannelQuery) -> GetChannelResultDTO:
        """Возвращает конкретный DTO сценария чтения."""
        return await self.repository.get_channel(query)
